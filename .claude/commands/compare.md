---
description: 최근 두 로그 파일 비교 분석
allowed-tools: Bash, Read
---

현재 logs 디렉토리 상태: !`ls -lht logs/*.json 2>/dev/null | head -5`

다음 명령어를 실행해주세요:

```bash
source .venv/bin/activate && python scripts/compare_runs.py --recent
```
