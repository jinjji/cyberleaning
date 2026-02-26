#!/usr/bin/env python3
"""Discord webhook 403 diagnosis with structured JSONL logging."""
from __future__ import annotations

import json
import socket
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def mask_webhook_url(url: str) -> str:
    # https://discord.com/api/webhooks/<id>/<token>
    parts = url.split("/")
    if len(parts) < 2:
        return "***"
    if len(parts) >= 2:
        parts[-1] = "***TOKEN***"
    return "/".join(parts)


def safe_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in {"authorization", "cookie", "set-cookie"}:
            continue
        out[k] = v
    return out


def snippet(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def record(log_file: Path, entry: dict[str, Any]) -> None:
    with log_file.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_dns_test(host: str) -> dict[str, Any]:
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        addrs = sorted({x[4][0] for x in infos})
        return {"ok": True, "addresses": addrs[:10]}
    except Exception as e:
        return {"ok": False, "error_type": type(e).__name__, "error_message": str(e)}


def run_tls_handshake(host: str, port: int = 443) -> dict[str, Any]:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return {
                    "ok": True,
                    "tls_version": ssock.version(),
                    "cipher": ssock.cipher()[0] if ssock.cipher() else None,
                    "subject": cert.get("subject"),
                    "issuer": cert.get("issuer"),
                }
    except Exception as e:
        return {"ok": False, "error_type": type(e).__name__, "error_message": str(e)}


def post_webhook(
    webhook_url: str,
    payload: dict[str, Any],
    *,
    wait: bool = False,
    user_agent: str | None = None,
) -> dict[str, Any]:
    url = webhook_url + ("?wait=true" if wait else "")
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if user_agent:
        headers["User-Agent"] = user_agent
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "ignore")
            return {
                "ok": True,
                "http_status": resp.status,
                "response_headers": safe_headers(dict(resp.headers.items())),
                "response_body_snippet": snippet(body),
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")
        except Exception:
            pass
        return {
            "ok": False,
            "http_status": e.code,
            "error_type": "HTTPError",
            "error_message": str(e),
            "response_headers": safe_headers(dict(e.headers.items())) if e.headers else {},
            "response_body_snippet": snippet(body),
        }
    except urllib.error.URLError as e:
        return {
            "ok": False,
            "error_type": "URLError",
            "error_message": str(e.reason),
        }
    except Exception as e:
        return {
            "ok": False,
            "error_type": type(e).__name__,
            "error_message": str(e),
        }


def run_curl_equivalent(webhook_url: str) -> dict[str, Any]:
    cmd = [
        "curl",
        "-sS",
        "-o",
        "-",
        "-w",
        "\n__STATUS__:%{http_code}",
        "-H",
        "Content-Type: application/json",
        "-H",
        "User-Agent: webhook-diag-curl/1.0",
        "-d",
        '{"content":"diag-curl-ping"}',
        webhook_url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return {"ok": False, "error_type": "MissingDependency", "error_message": "curl not found"}
    except Exception as e:
        return {"ok": False, "error_type": type(e).__name__, "error_message": str(e)}

    output = proc.stdout or ""
    status = None
    if "__STATUS__:" in output:
        body, _, tail = output.rpartition("__STATUS__:")
        output = body
        try:
            status = int(tail.strip())
        except Exception:
            status = None
    ok = status is not None and 200 <= status < 300
    return {
        "ok": ok,
        "http_status": status,
        "response_body_snippet": snippet(output.strip()),
        "stderr_snippet": snippet((proc.stderr or "").strip()),
    }


def detect_likely_cause(results: list[dict[str, Any]]) -> str:
    post_results = [r for r in results if r.get("test_id") in {"T4", "T5", "T6", "T7", "T8"}]
    statuses = [r.get("http_status") for r in post_results if r.get("http_status") is not None]
    body_text = "\n".join(r.get("response_body_snippet", "") for r in post_results)
    headers_text = json.dumps(
        [r.get("response_headers", {}) for r in post_results], ensure_ascii=False
    ).lower()

    if any(s == 204 for s in statuses):
        return "inconclusive"
    if statuses and all(s == 403 for s in statuses):
        if "unknown webhook" in body_text.lower() or '"code": 10015' in body_text:
            return "likely_invalid_or_revoked_webhook"
        if "discord" not in headers_text and ("<html" in body_text.lower() or "forbidden" in body_text.lower()):
            return "likely_proxy_or_waf_block"
        return "likely_permission_or_channel_policy"
    if any(s in {401, 404} for s in statuses):
        return "likely_invalid_or_revoked_webhook"
    if any("URLError" == r.get("error_type") for r in post_results):
        return "likely_proxy_or_waf_block"
    return "inconclusive"


def main() -> int:
    project_root = Path(__file__).parent.parent
    env = load_env(project_root / ".env")
    webhook_url = env.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("❌ .env에 DISCORD_WEBHOOK_URL이 없습니다.")
        return 1

    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"webhook_diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    masked = mask_webhook_url(webhook_url)
    parsed = urllib.parse.urlparse(webhook_url)
    webhook_host = parsed.hostname or "discord.com"

    print("🔎 Discord webhook 진단 시작")
    print(f"   target: {masked}")
    print(f"   log: {log_file}")

    results: list[dict[str, Any]] = []

    t1 = {
        "ts": now_iso(),
        "test_id": "T1",
        "step": "url_format_check",
        "ok": webhook_url.startswith("https://discord.com/api/webhooks/") and (" " not in webhook_url),
        "request_meta": {
            "masked_webhook_url": masked,
            "url_length": len(webhook_url),
            "has_quote": '"' in webhook_url or "'" in webhook_url,
        },
    }
    results.append(t1)
    record(log_file, t1)

    t2_data = run_dns_test("discord.com")
    t2 = {"ts": now_iso(), "test_id": "T2", "step": "dns_discord.com", **t2_data}
    results.append(t2)
    record(log_file, t2)

    t2b_data = run_dns_test(webhook_host)
    t2b = {"ts": now_iso(), "test_id": "T2b", "step": f"dns_{webhook_host}", **t2b_data}
    results.append(t2b)
    record(log_file, t2b)

    t3_data = run_tls_handshake("discord.com")
    t3 = {"ts": now_iso(), "test_id": "T3", "step": "tls_handshake_discord.com", **t3_data}
    results.append(t3)
    record(log_file, t3)

    tests = [
        ("T4", "post_minimal", {"content": "diag-minimal-ping"}, False, None, "minimal", "default"),
        (
            "T5",
            "post_embed",
            {"content": "diag-embed-ping", "embeds": [{"title": "diag", "description": "embed"}]},
            False,
            None,
            "embed",
            "default",
        ),
        ("T6", "post_minimal_wait_true", {"content": "diag-wait-ping"}, True, None, "minimal", "default"),
        (
            "T7",
            "post_minimal_custom_ua",
            {"content": "diag-custom-ua-ping"},
            False,
            "webhook-diag-python/1.0",
            "minimal",
            "custom",
        ),
    ]
    for tid, step, payload, wait, ua, ptype, ua_type in tests:
        data = post_webhook(webhook_url, payload, wait=wait, user_agent=ua)
        entry = {
            "ts": now_iso(),
            "test_id": tid,
            "step": step,
            **data,
            "request_meta": {"payload_type": ptype, "ua_type": ua_type, "wait_flag": wait},
        }
        results.append(entry)
        record(log_file, entry)

    t8_data = run_curl_equivalent(webhook_url)
    t8 = {
        "ts": now_iso(),
        "test_id": "T8",
        "step": "curl_equivalent_post",
        **t8_data,
        "request_meta": {"payload_type": "minimal", "ua_type": "curl", "wait_flag": False},
    }
    results.append(t8)
    record(log_file, t8)

    classification = detect_likely_cause(results)
    summary = {
        "ts": now_iso(),
        "test_id": "SUMMARY",
        "step": "classification",
        "ok": classification == "inconclusive",
        "classification": classification,
        "result_count": len(results),
    }
    record(log_file, summary)

    print("\n📊 진단 요약")
    for r in results:
        code = r.get("http_status")
        if code is not None:
            print(f" - {r['test_id']}: {'OK' if r.get('ok') else 'FAIL'} (HTTP {code})")
        else:
            print(f" - {r['test_id']}: {'OK' if r.get('ok') else 'FAIL'}")
    print(f" - CLASSIFICATION: {classification}")
    print(f"\n📝 상세 로그: {log_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
