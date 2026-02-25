# UI Automation Starter Kit (PyAutoGUI)

이 키트는 화면 이미지 매칭 기반 자동화를 빠르게 재시작하기 위한 기본 세트입니다.

## 포함 파일
- `runner_starter.py`: 상태머신 기반 자동화 러너 템플릿
- `template_quality_check.py`: 템플릿 매칭 품질 점검
- `capture_from_cursor.py`: 커서 주변 캡처 + 템플릿 후보 생성
- `config_example.py`: 프로젝트별 설정 샘플
- `validation_checklist.md`: 검증 시나리오 체크리스트

## 빠른 시작
1. 프로젝트 루트에 `assets/` 폴더를 만들고 템플릿 이미지를 둡니다.
2. `config_example.py`를 복사해 `config.py`로 저장 후 경로/좌표를 수정합니다.
3. `capture_from_cursor.py`로 START 버튼 템플릿 후보를 캡처합니다.
4. `template_quality_check.py`로 품질(LEFT 매칭/점수) 확인합니다.
5. `runner_starter.py`를 실행해 상태 전환 로그를 확인합니다.

## 권장 실행 순서
1. `python capture_from_cursor.py`
2. `python template_quality_check.py`
3. `python runner_starter.py`

## 환경 주의
- macOS 권한: `Screen Recording`, `Accessibility` 허용 필요
- Retina 환경에서는 좌표 스케일 보정이 필수
- 브라우저 zoom은 `100%`로 고정 권장
