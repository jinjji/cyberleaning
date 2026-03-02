---
description: venv 활성화 후 runner.py 실행 및 Discord 알림
allowed-tools: Bash, Read
---

다음 순서로 실행해주세요:

## 1. runner.py 실행

```bash
source .venv/bin/activate && python runner.py
```

## 2. 실행 완료 후 처리

실행이 완료되면 다음 단계를 수행해주세요:

### 2-1. 최신 로그 파일 확인
```bash
ls -t logs/run_*.json | head -1
```

### 2-2. 로그 파일 파싱
위에서 확인한 로그 파일을 Read 도구로 읽어 다음 항목들을 파싱하세요:
- **완료 강의 수**: `event_type: "state_transition"`, `from: "S4_WAIT_EXIT"`, `to: "S0_LIST_WAIT_START"` 이벤트의 개수
- **소요 시간**: 로그의 첫 이벤트 timestamp와 마지막 이벤트 timestamp의 차이 (분 단위, 소수점 1자리)
- **에러 발생 건수**: `event_type: "error"` 또는 `event_type: "exception"`인 이벤트의 개수

### 2-3. .env 파일에서 Discord 웹훅 URL 추출
`.env` 파일을 Read 도구로 읽어 `DISCORD_WEBHOOK_URL` 값을 추출하세요.

### 2-4. fetch MCP로 Discord 웹훅 알림 전송

fetch MCP를 사용하여 다음과 같은 JSON embed를 Discord로 전송합니다:

```json
{
  "embeds": [{
    "title": "🤖 runner.py 실행 완료",
    "color": 3066993,
    "fields": [
      {"name": "✅ 완료 강의", "value": "[완료 강의 수]개", "inline": true},
      {"name": "⏱️ 소요 시간", "value": "[소요 시간]분", "inline": true},
      {"name": "❌ 에러 발생", "value": "[에러 건수]건 또는 없음", "inline": false},
      {"name": "📝 로그 파일", "value": "`[로그 파일명]`", "inline": false}
    ],
    "footer": {"text": "Claude Code Runner Notifier"}
  }]
}
```

fetch MCP 호출 명령어:
- **URL**: 위에서 추출한 `DISCORD_WEBHOOK_URL` 값
- **Method**: POST
- **Body**: 위의 JSON embed

fetch MCP 전송 후 HTTP 200 상태 코드를 확인하면 성공입니다.
