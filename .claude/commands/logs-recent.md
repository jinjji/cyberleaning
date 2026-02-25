---
description: 최근 로그 목록 및 최신 로그 내용 확인
allowed-tools: Bash, Read
---

최근 로그 목록: !`ls -lht logs/*.json 2>/dev/null | head -10`

최신 로그 마지막 내용: !`tail -20 "$(ls -t logs/*.json 2>/dev/null | head -1)" 2>/dev/null || echo "로그 없음"`
