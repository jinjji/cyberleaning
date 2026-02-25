# Validation Checklist

## A. 템플릿 품질
- [ ] `python capture_from_cursor.py`로 후보 템플릿 생성
- [ ] 필요 시 `assets/IMG_START_candidate.png` -> `assets/IMG_START.png` 교체
- [ ] `python template_quality_check.py` 실행
- [ ] `LEFT best score >= 0.90` 확인
- [ ] `conf >= 0.90`에서 LEFT 매칭 존재 확인

## B. 러너 단일 사이클
- [ ] `python runner_starter.py` 실행
- [ ] `S0 -> S1 -> S2 -> S3 -> S4 -> S0` 로그 확인
- [ ] `S3 timeout` 발생 시에도 S4로 복구 확인

## C. 반복 안정성
- [ ] 3사이클 연속 비정상 종료 없음
- [ ] START 좌표가 의도한 영역(왼쪽)으로 유지
- [ ] 고정 클릭 좌표(BASE_X, BASE_Y)가 실제 동작에 유효
