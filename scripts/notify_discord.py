#!/usr/bin/env python3
"""Discord 웹훅을 통해 runner.py 실행 결과를 알림"""
import json
import subprocess
from pathlib import Path
from datetime import datetime


def load_env(env_path):
    """key=value 형식의 .env 파일 파싱"""
    if not env_path.exists():
        return {}
    result = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def get_latest_log():
    """최신 로그 파일 경로와 내용 반환"""
    logs_dir = Path(__file__).parent.parent / "logs"
    log_files = sorted(logs_dir.glob("run_*.json"), reverse=True)
    if not log_files:
        return None, None
    return log_files[0], log_files[0]


def parse_log(log_path):
    """로그 파일 파싱 (NDJSON 형식)"""
    events = []
    if not log_path.exists():
        return events

    for line in log_path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def count_completed_lectures(events):
    """S4_WAIT_EXIT → S0_LIST_WAIT_START 상태 전이 횟수 카운트"""
    count = 0
    for event in events:
        details = event.get("details", {})
        if (
            event.get("event_type") == "state_transition"
            and details.get("from") == "S4_WAIT_EXIT"
            and details.get("to") == "S0_LIST_WAIT_START"
        ):
            count += 1
    return count


def get_elapsed_time(events):
    """로그 첫 이벤트부터 마지막 이벤트까지 경과 시간 (분)"""
    if not events:
        return 0

    timestamps = []
    for event in events:
        if "timestamp" in event:
            timestamps.append(event["timestamp"])

    if len(timestamps) < 2:
        return 0

    try:
        start = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
        end = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
        elapsed_minutes = (end - start).total_seconds() / 60
        return round(elapsed_minutes, 1)
    except (ValueError, IndexError):
        return 0


def count_errors(events):
    """로그에서 에러 이벤트 카운트"""
    count = 0
    for event in events:
        if event.get("event_type") in ("error", "exception"):
            count += 1
    return count


def send_discord_notification(webhook_url, log_path, completed, elapsed_minutes, error_count):
    """Discord 웹훅으로 알림 전송 (curl 기반)."""
    log_name = log_path.name

    message = {
        "embeds": [{
            "title": "🤖 runner.py 실행 완료",
            "color": 3066993 if error_count == 0 else 15158332,
            "fields": [
                {"name": "✅ 완료 강의", "value": f"{completed}개", "inline": True},
                {"name": "⏱️ 소요 시간", "value": f"{elapsed_minutes}분", "inline": True},
                {"name": "❌ 에러 발생", "value": "없음" if error_count == 0 else f"{error_count}건", "inline": False},
                {"name": "📝 로그 파일", "value": f"`{log_name}`", "inline": False},
            ],
            "footer": {"text": "Claude Code Runner Notifier"}
        }]
    }

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
        "User-Agent: webhook-notify-curl/1.0",
        "-d",
        json.dumps(message, ensure_ascii=False),
        webhook_url,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
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
            print(f"✅ Discord 알림 전송 성공 ({log_name}) [HTTP {status}]")
            return True

        if status is None:
            print("❌ Discord 알림 전송 실패: HTTP 상태 코드를 파싱하지 못했습니다")
        else:
            print(f"❌ Discord 알림 전송 실패: HTTP {status}")
        if body.strip():
            print(f"   response: {body.strip()[:500]}")
        if err:
            print(f"   curl stderr: {err[:500]}")
        return False
    except FileNotFoundError:
        print("❌ Discord 알림 전송 실패: curl not found")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False


def main():
    """메인 함수"""
    # .env 파일에서 Discord 웹훅 URL 로드
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    env_vars = load_env(env_path)
    webhook_url = env_vars.get("DISCORD_WEBHOOK_URL", "").strip()

    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL이 설정되지 않았습니다 (.env 파일 확인)")
        exit(1)

    # 최신 로그 파일 찾기
    log_path, _ = get_latest_log()
    if not log_path:
        print("❌ 로그 파일을 찾을 수 없습니다")
        exit(1)

    # 로그 파싱 및 통계 계산
    events = parse_log(log_path)
    completed = count_completed_lectures(events)
    elapsed_minutes = get_elapsed_time(events)
    error_count = count_errors(events)

    # Discord 알림 전송
    success = send_discord_notification(webhook_url, log_path, completed, elapsed_minutes, error_count)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
