# Compare Runs 커맨드 가이드

자동화 실행 로그를 비교하여 성공/실패 원인을 분석하는 도구입니다.

## 설치

이미 완성되어 있습니다! 다음 파일들이 자동으로 생성되었습니다:
- `runner.py` - JSON 로깅 기능이 추가된 메인 러너
- `compare_runs.py` - 로그 비교 분석 스크립트
- `logs/` - 로그 저장 디렉토리 (자동 생성)

## 사용 방법

### 1단계: 자동화 실행 후 로그 저장

#### 성공한 실행 저장
```bash
# venv 활성화
source .venv/bin/activate

# 자동화 실행 (완전히 끝날 때까지)
python runner.py
```

성공하면:
```
[LOG] JSON log saved to: logs/run_20260225_100000.json
```

#### 실패한 실행 저장
같은 방식으로 실패하는 상황에서 `runner.py`를 실행합니다:
```bash
python runner.py
# 실패 후 Ctrl+C로 중단
```

### 2단계: 로그 비교

#### 방법 1: 구체적인 파일 지정
```bash
python compare_runs.py logs/run_20260225_100000.json logs/run_20260225_100500.json
```

#### 방법 2: 최근 2개 로그 자동 선택 (추천)
```bash
python compare_runs.py --recent
```

## 분석 결과 읽는 방법

### [1] 상태 전환 타임라인 비교
```
✓ 성공한 실행:
  0s: START
  0.5s: S0_LIST_WAIT_START -> S1_PLAYER_FOCUS
  2.1s: S1_PLAYER_FOCUS -> S2_WATCHING_WAIT_POPUP1
  4.3s: S2_WATCHING_WAIT_POPUP1 -> S3_WAIT_POPUP2
  ...

✗ 실패한 실행:
  0s: START
  0.5s: S0_LIST_WAIT_START -> S1_PLAYER_FOCUS
  (여기서 멈춤)
```

**읽는 법**:
- 실패 실행에서 상태 전환이 부족하면 그 지점에서 문제 발생
- 특정 상태에 머물렀다면 템플릿 감지 실패일 가능성

### [2] 템플릿 감지 통계
```
  START        | 성공: 3회  |  실패: 5회  ⚠️  (2회 더 많음)
  POPUP1       | 성공: 1회  |  실패: 0회
  EXIT         | 성공: 1회  |  실패: 0회
```

**읽는 법**:
- ⚠️ 표시: 실패 로그에서 같은 템플릿을 더 많이 감지하려 시도
- 이는 해당 템플릿이 불안정함을 의미
- **개선**: 템플릿 이미지 품질 확인, CONFIDENCE 값 조정

### [3] 클릭 이벤트 분석
```
성공: 5회 클릭
  - START              at (500, 400)
  - PLAYER(fixed)      at (960, 620)
  - ...

실패: 2회 클릭
  - START              at (505, 398)
  - PLAYER(fixed)      at (960, 620)
```

**읽는 법**:
- 클릭 위치의 차이로 화면 상태 변화 감지 가능
- 실패 로그에서 클릭이 적으면 중간에 중단된 것

### [4] 타임아웃 분석
```
실패 중 타임아웃 발생: 1회
  - 5초 제한 중 5.2초 경과
```

**읽는 법**:
- S3 상태(POPUP2 대기)에서 시간이 초과될 수 있음
- `S3_TIMEOUT` 값을 늘려야 할 수도 있음

### [5] 개선 제안 (자동 생성)
```
• 'START' 템플릿: 감지 실패율이 높습니다.
  템플릿 품질을 점검하거나 CONFIDENCE 값을 조정해보세요.

• 상태 전환이 2회 부족합니다.
  특정 상태에서 멈추거나 오류가 발생했을 가능성이 있습니다.
```

## 문제 해결 시나리오

### 시나리오 1: START 템플릿이 자주 감지 안 됨
```
START | 성공: 1회 | 실패: 5회 ⚠️
```

**해결 방법**:
```bash
# 1. START 템플릿 다시 캡처
python starter_kit/capture_from_cursor.py

# 2. 품질 확인
python starter_kit/template_quality_check.py

# 3. runner.py의 CONFIDENCE 값을 낮춰보기
# runner.py 또는 config.py에서:
# CONFIDENCE = 0.85  (기본: 0.88)
```

### 시나리오 2: S3 상태에서 자주 타임아웃
```
실패 중 타임아웃 발생: 1회
  - 5초 제한 중 5.2초 경과
```

**해결 방법**:
```python
# runner.py에서 S3_TIMEOUT 증가
S3_TIMEOUT = 8.0  # 기본: 5.0
```

### 시나리오 3: 특정 상태에서 멈춤
```
✗ 실패한 실행:
  0s: START
  0.5s: S0 -> S1
  (S1에서 멈춤)
```

**해결 방법**:
1. S1 상태의 PLAYER 클릭이 제대로 작동하는지 확인
2. 좌표 설정 확인: `BASE_X`, `BASE_Y`
3. 화면 해상도 변경 확인

## 팁

### 자동으로 최근 로그 비교
```bash
# 최근 2개 로그를 자동으로 비교
python compare_runs.py --recent
```

### 여러 번 실행하여 경향성 파악
```bash
# 성공 1회
python runner.py
# → logs/run_20260225_100000.json

# 실패 1회
python runner.py
# → logs/run_20260225_100100.json

# 비교
python compare_runs.py --recent

# 반복하여 일관성 있는 문제 찾기
```

### 로그 정리
```bash
# 오래된 로그 삭제 (선택사항)
rm logs/run_*.json

# 또는 특정 로그 백업
cp logs/run_20260225_100000.json logs/backup_successful.json
```

## JSON 로그 구조 (참고)

각 로그 파일은 JSON Lines 형식입니다:
```json
{"timestamp": "2026-02-25T10:30:00.123", "message": "[INIT] scale x=2.000...", "event_type": "init", "details": {...}}
{"timestamp": "2026-02-25T10:30:00.456", "message": "[S0] START hit 2/2...", "event_type": "detection", "details": {...}}
{"timestamp": "2026-02-25T10:30:01.789", "message": "[CLICK] START...", "event_type": "click", "details": {...}}
```

이를 통해 원시 데이터가 필요하면 직접 분석할 수도 있습니다.
