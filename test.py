#!/usr/bin/env python3
"""Discord webhook quick health check using curl only."""
import json
import subprocess
from pathlib import Path


def load_webhook_url(env_path: Path) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == "DISCORD_WEBHOOK_URL":
            return v.strip()
    return ""


def mask_webhook_url(url: str) -> str:
    parts = url.split("/")
    if len(parts) >= 2:
        parts[-1] = "***TOKEN***"
    return "/".join(parts)


def main() -> int:
    env_path = Path(__file__).parent / ".env"
    webhook_url = load_webhook_url(env_path)
    if not webhook_url:
        print("❌ .env에서 DISCORD_WEBHOOK_URL을 찾을 수 없습니다")
        return 1

    payload = {"content": "[Webhook Test] curl path"}
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
        "User-Agent: webhook-test-curl/1.0",
        "-d",
        json.dumps(payload, ensure_ascii=False),
        webhook_url,
    ]

    print("📤 Sending webhook health-check message via curl...")
    print(f"   target: {mask_webhook_url(webhook_url)}")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        print("❌ curl not found")
        return 1
    except Exception as e:
        print(f"❌ curl 실행 실패: {e}")
        return 1

    out = proc.stdout or ""
    err = (proc.stderr or "").strip()
    status = None
    body = out
    if "__STATUS__:" in out:
        body, _, tail = out.rpartition("__STATUS__:")
        try:
            status = int(tail.strip())
        except ValueError:
            status = None

    if status is not None and 200 <= status < 300:
        print(f"✅ 성공 (HTTP {status})")
        return 0

    if status is None:
        print("❌ 실패: HTTP 상태 코드를 파싱하지 못했습니다")
    else:
        print(f"❌ 실패 (HTTP {status})")

    body = body.strip()
    if body:
        print(f"   response: {body[:500]}")
    if err:
        print(f"   curl stderr: {err[:500]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
