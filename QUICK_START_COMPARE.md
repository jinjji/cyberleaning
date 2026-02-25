# Compare Runs 빠른 시작 (5분)

## 단계별 실행

### 1단계: venv 활성화 (30초)
```bash
source .venv/bin/activate
```

### 2단계: 성공한 실행 저장 (1-2분)
```bash
# 자동화를 완전히 끝날 때까지 실행
python runner.py

# 완료되면:
# [LOG] JSON log saved to: logs/run_20260225_103000.json
```

### 3단계: 실패한 실행 저장 (1-2분)
같은 방식으로 실패하는 상황에서:
```bash
python runner.py
# 실패 또는 특정 상태에서 멈추면 Ctrl+C로 중단

# 완료되면:
# [LOG] JSON log saved to: logs/run_20260225_103100.json
```

### 4단계: 자동 비교 (10초)
```bash
# 최근 2개 로그를 자동으로 비교
python compare_runs.py --recent
```

## 결과 해석 (예시)

```
========================================
자동화 실행 로그 비교 분석
========================================

✓ 성공 로그: run_20260225_103000.json (850 항목)
✗ 실패 로그: run_20260225_103100.json (450 항목)

[1] 상태 전환 타임라인 비교
──────────────────────────────────────
✓ 성공한 실행:
  0s: START
  0.5s: S0_LIST_WAIT_START -> S1_PLAYER_FOCUS
  2.1s: S1_PLAYER_FOCUS -> S2_WATCHING_WAIT_POPUP1
  4.3s: S2_WATCHING_WAIT_POPUP1 -> S3_WAIT_POPUP2
  6.8s: S3_WAIT_POPUP2 -> S4_WAIT_EXIT

✗ 실패한 실행:
  0s: START
  0.5s: S0_LIST_WAIT_START -> S1_PLAYER_FOCUS
  (여기서 멈춤 - S1 상태를 벗어나지 못함)

[2] 템플릿 감지 통계
──────────────────────────────────────
  START        | 성공: 3회  |  실패: 8회  ⚠️  (5회 더 많음)
  POPUP1       | 성공: 1회  |  실패: 0회
  POPUP2       | 성공: 1회  |  실패: 0회
  EXIT         | 성공: 1회  |  실패: 0회

[3] 클릭 이벤트 분석
──────────────────────────────────────
성공: 5회 클릭
  - START              at (450, 380)
  - PLAYER(fixed)      at (960, 620)
  - ...

실패: 1회 클릭
  - START              at (455, 378)

[4] 타임아웃 분석
──────────────────────────────────────
타임아웃 없음

[5] 개선 제안
──────────────────────────────────────
• 'START' 템플릿: 감지 실패율이 높습니다.
  템플릿 품질을 점검하거나 CONFIDENCE 값을 조정해보세요.

• 상태 전환이 5회 부족합니다.
  특정 상태에서 멈추거나 오류가 발생했을 가능성이 있습니다.
```

## 분석 결과 읽기

### ✓ 성공 로그
- 모든 상태를 순서대로 통과
- 일관된 템플릿 감지
- 예상한 클릭 수행

### ✗ 실패 로그
- **S1에서 멈춤** ← 문제 지점!
  - S1은 PLAYER(fixed) 클릭 상태
  - 이 후 S2로 전환되어야 함
  - 전환 안 됨 = 무언가 차단됨

### ⚠️ 개선 제안
**START 템플릿 감지 실패율 높음**
- 실패 로그에서 START를 5회나 더 감지 시도
- = 템플릿이 화면에 제대로 매칭 안 됨

## 다음 액션

### A. START 템플릿 개선
```bash
# 1. 새로운 START 템플릿 캡처
python starter_kit/capture_from_cursor.py

# 2. 품질 확인
python starter_kit/template_quality_check.py

# 3. 다시 테스트
python runner.py
python compare_runs.py --recent
```

### B. CONFIDENCE 값 조정 (더 빠른 방법)
```bash
# runner.py 또는 config.py에서:
# CONFIDENCE = 0.85  # 0.88에서 0.05 낮춤

python runner.py
python compare_runs.py --recent
```

### C. S1 상태 확인
```bash
# runner.py에서 S1_CLICK_MODE 확인:
# S1_CLICK_MODE = "FIXED"  # 고정 좌표 클릭
# 또는
# S1_CLICK_MODE = "TEMPLATE"  # 템플릿 기반 클릭

# BASE_X, BASE_Y 좌표가 올바른지 확인
# 현재 화면 해상도와 일치하는지 확인
```

## 팁 & 트릭

### 🚀 반복 테스트
```bash
# 3회 반복 수행 후 통계 비교
for i in {1..3}; do python runner.py; done

# 처음 2개 비교
python compare_runs.py --recent
```

### 📊 구체적인 파일 지정
```bash
# 특정 로그 파일 비교
python compare_runs.py \
  logs/run_20260225_103000.json \
  logs/run_20260225_103100.json
```

### 📁 로그 정리
```bash
# 최근 로그 백업
cp logs/run_*.json logs/backup_$(date +%s).tar

# 오래된 로그 삭제
rm logs/run_*.json
```

### 🔗 모든 문서 읽기
- [상세 가이드](COMPARE_RUNS_GUIDE.md) - 모든 기능 설명
- [검증 시나리오](validation_scenarios.md) - 테스트 시나리오
- [Starter Kit](starter_kit/README.md) - 템플릿 작업

## 자주 묻는 질문

### Q: 로그 파일은 어디에 저장되나요?
A: `logs/` 디렉토리에 자동으로 저장됩니다.
   파일명은 `run_YYYYMMDD_HHMMSS.json` 형식입니다.

### Q: 성공/실패 순서가 중요한가요?
A: 아니요. `--recent`를 사용하면 최신 2개를 자동으로 비교합니다.
   순서는 상관없습니다.

### Q: 로그를 여러 번 실행해서 모을 수 있나요?
A: 네! 여러 번 실행하면 각각 다른 파일로 저장되므로
   원하는 2개를 선택해서 비교할 수 있습니다.

### Q: JSON 로그를 직접 분석할 수 있나요?
A: 네! `logs/run_*.json`은 JSON Lines 형식이므로
   직접 읽거나 다른 도구로 분석할 수 있습니다.

---

**전체 가이드는 [COMPARE_RUNS_GUIDE.md](COMPARE_RUNS_GUIDE.md)를 참고하세요!**
