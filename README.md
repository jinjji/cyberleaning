# RPA 자동화 테스트 프로젝트

UI 자동화 및 템플릿 매칭을 기반으로 한 RPA(Robotic Process Automation) 테스트 프레임워크입니다.

## 📋 프로젝트 구조

```
.
├── runner.py                 # 메인 자동화 스크립트 (JSON 로깅 추가)
├── requirements.txt          # 프로젝트 의존성
│
├── scripts/                  # 🆕 분석 스크립트 모음
│   ├── compare_runs.py       # 로그 비교 분석 스크립트
│   ├── diagnose.py           # 최신 로그 진단 스크립트
│   └── stats.py              # 전체 로그 통계 생성
│
├── tools/                    # 🆕 개발 유틸리티
│   ├── runner_starter.py     # 스타터 템플릿
│   ├── config_example.py     # 설정 샘플
│   ├── capture_from_cursor.py # 커서 위치 캡처 유틸
│   ├── template_quality_check.py # 템플릿 품질 검사
│   └── README.md             # tools 사용 가이드
│
├── docs/                     # 🆕 문서 모음
│   ├── COMPARE_RUNS_GUIDE.md # 로그 분석 가이드
│   ├── QUICK_START_COMPARE.md # 빠른 시작 가이드
│   └── validation_scenarios.md # 검증 시나리오
│
├── assets/                   # 이미지 템플릿 (별도 저장소)
├── logs/                     # 자동화 실행 JSON 로그 (자동 생성)
└── .venv/                    # Python 가상환경
```

## 🚀 시작하기

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/jinjji/[저장소명]
cd test

# 의존성 설치
pip install -r requirements.txt
```

### 2. 설정

```bash
# tools의 config_example.py를 참고하여 설정 구성
cp tools/config_example.py config.py
# config.py 파일에서 필요한 설정 수정
```

### 3. 실행

```bash
# 메인 자동화 스크립트 실행
python runner.py
```

## 📦 주요 모듈

### runner.py
- 전체 자동화 플로우를 제어하는 메인 스크립트
- 상태 머신(State Machine) 기반 동작
- 이미지 템플릿 매칭을 통한 UI 요소 감지

### tools 폴더의 개발 유틸리티

#### config_example.py
- 템플릿 경로 설정
- 탐지 민감도 및 동작 파라미터
- 로그 정책 설정

#### runner_starter.py
- 기본 자동화 템플릿

#### capture_from_cursor.py
- 커서 위치 기반 스크린샷 캡처
- 템플릿 추출 유틸리티

#### template_quality_check.py
- 템플릿 품질 검증
- 이미지 유사도 분석

자세한 내용은 [tools/README.md](tools/README.md) 참고

## ⚙️ 주요 기능

### 상태 관리
- **S0**: START 버튼 대기 및 클릭
- **S1**: 플레이어 포커스
- **S2**: POPUP1 대기
- **S3**: POPUP2 대기
- **S4**: EXIT 버튼 대기

### 이미지 감지
- pyautogui/pyscreeze를 이용한 템플릿 매칭
- OpenCV 기반 고급 분석
- 감지 안정화 (REQUIRE_HITS로 오탐지 방지)

### 커스터마이제이션
- 신뢰도(CONFIDENCE) 조정
- 스캔 간격 설정
- 상태별 타임아웃 설정
- 고정 클릭/템플릿 기반 클릭 선택

## 🔧 설정 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| CONFIDENCE | 이미지 매칭 신뢰도 | 0.88 |
| REQUIRE_HITS | 감지 확인 횟수 | 2 |
| SCAN_INTERVAL | 스캔 간격(초) | 0.3 |
| CLICK_COOLDOWN | 클릭 후 대기 시간 | 2.0 |
| START_PRECHECK_TRIES | START 사전 확인 횟수 | 5 |
| S3_TIMEOUT | S3 상태 타임아웃(초) | 5.0 |

## 📝 로그

### SIMPLE_LOG = True
간단한 로그 출력 (권장)
```
[S0] START hit 2/2 at (500,600)
[CLICK] START (500,600)
```

### DEBUG_MODE = True
상세한 디버그 정보 및 히스토리

## 🧪 Webhook 점검

### 빠른 단일 확인 (`test.py`)
- 목적: 웹훅이 지금 바로 전송 가능한지 빠르게 체크 (curl 단독 경로)
- 실행:
```bash
python test.py
```

### 상세 원인 진단 (`scripts/diagnose_webhook.py`)
- 목적: 403 원인을 단계별로 분리 (DNS/TLS/POST payload/curl 비교)
- 실행:
```bash
python scripts/diagnose_webhook.py
```
- 결과:
  - 콘솔 요약
  - `logs/webhook_diag_YYYYMMDD_HHMMSS.jsonl` 상세 로그

### runner.py 알림 경로
- `runner.py` 자체는 디스코드 전송 코드를 직접 실행하지 않습니다.
- 실제 알림 전송은 `.claude`의 Post 훅에서 `scripts/notify_discord.py`를 호출해 처리합니다.
- `scripts/notify_discord.py`는 curl 경로로 전송합니다.

## 🔍 로그 분석 - Compare Runs 커맨드

**새로운 기능!** 성공/실패한 실행 로그를 자동으로 비교하여 문제점을 분석합니다.

### 사용 방법

```bash
# 1. 성공한 실행 저장
python runner.py
# logs/run_20260225_100000.json 저장됨

# 2. 실패한 실행 저장
python runner.py
# logs/run_20260225_100100.json 저장됨

# 3. 로그 비교 분석
python scripts/compare_runs.py --recent
```

### 분석 결과 예시

```
[1] 상태 전환 타임라인 비교
  ✓ 성공: S0 -> S1 -> S2 -> S3 -> S4 -> S0 (완전한 사이클)
  ✗ 실패: S0 -> S1 (S1에서 멈춤)

[2] 템플릿 감지 통계
  START   | 성공: 3회 | 실패: 5회 ⚠️
  POPUP1  | 성공: 1회 | 실패: 0회

[5] 개선 제안
  • 'START' 템플릿: 감지 실패율이 높습니다.
    템플릿 품질을 점검하거나 CONFIDENCE 값을 조정해보세요.
```

### 주요 기능

✅ 상태 전환 타임라인 비교
✅ 템플릿 감지 통계 분석
✅ 클릭 이벤트 추적
✅ 타임아웃 분석
✅ 자동 개선 제안

자세한 가이드는 [docs/COMPARE_RUNS_GUIDE.md](docs/COMPARE_RUNS_GUIDE.md) 참고

## ⚠️ 주의사항

- `assets` 폴더의 이미지 템플릿은 별도로 관리됩니다
- 자동화 실행 중 `Ctrl+C`로 언제든 중단 가능합니다
- 이미지 템플릿은 대상 해상도에 맞게 준비되어야 합니다
- FAILSAFE 모드는 활성화되어 있습니다 (화면 모서리 접근 시 중단)

## 📧 기술 스택

- **Python 3.7+**
- **pyautogui**: 마우스/키보드 제어
- **opencv-python**: 이미지 처리 및 분석
- **Pillow**: 이미지 유틸리티
- **NumPy**: 수치 계산

## 📄 라이센스

개인 프로젝트

## 🔗 관련 파일

- [검증 시나리오](docs/validation_scenarios.md)
- [Tools 가이드](tools/README.md)
- [로그 비교 가이드](docs/COMPARE_RUNS_GUIDE.md)
- [빠른 시작 가이드](docs/QUICK_START_COMPARE.md)
