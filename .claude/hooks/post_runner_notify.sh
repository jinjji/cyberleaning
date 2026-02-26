#!/bin/bash
# Post Hook: runner.py 실행 후 Discord 알림 전송

# 입력 JSON에서 명령어 추출
COMMAND=$(cat | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    print(cmd)
except:
    pass
")

# runner.py 실행이 아니면 그대로 종료
if ! echo "$COMMAND" | grep -qE "(python|python3).*runner\.py"; then
    exit 0
fi

# 프로젝트 루트로 이동
cd /Users/jinhyeok/coding/test || exit 0

# Discord 알림 전송 (notification_discord.py 실행)
# 실패해도 hook 자체는 성공으로 반환 (runner 실행이 이미 완료됨)
python3 scripts/notify_discord.py 2>&1 || true

exit 0
