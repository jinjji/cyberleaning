#!/usr/bin/env python3
"""
자동화 실행 로그 비교 도구

성공/실패한 자동화 로그를 비교하여:
- 상태 전환 타이밍 분석
- 템플릿 감지 신뢰도 비교
- 클릭 위치 분석
- 개선 포인트 제안
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any


class LogAnalyzer:
  """로그 파일 분석 클래스"""

  def __init__(self, log_file: Path):
    self.log_file = log_file
    self.entries = []
    self.load()

  def load(self):
    """JSON 라인 단위 로그 로드"""
    if not self.log_file.exists():
      print(f"[ERROR] 파일을 찾을 수 없음: {self.log_file}")
      return

    with open(self.log_file, "r") as f:
      for line in f:
        try:
          entry = json.loads(line.strip())
          self.entries.append(entry)
        except json.JSONDecodeError:
          pass

  def get_transitions(self) -> List[tuple]:
    """상태 전환 목록 반환"""
    transitions = []
    for entry in self.entries:
      if entry.get("event_type") == "state_transition":
        details = entry.get("details", {})
        transitions.append({
          "timestamp": entry.get("timestamp"),
          "from": details.get("from"),
          "to": details.get("to"),
          "reason": details.get("reason")
        })
    return transitions

  def get_detections(self) -> List[Dict[str, Any]]:
    """템플릿 감지 목록 반환"""
    detections = []
    for entry in self.entries:
      if entry.get("event_type") == "detection":
        details = entry.get("details", {})
        detections.append({
          "timestamp": entry.get("timestamp"),
          "template": details.get("template"),
          "hits": details.get("hits"),
          "required_hits": details.get("required_hits"),
          "center": details.get("center_logical")
        })
    return detections

  def get_clicks(self) -> List[Dict[str, Any]]:
    """클릭 이벤트 목록 반환"""
    clicks = []
    for entry in self.entries:
      if entry.get("event_type") == "click":
        details = entry.get("details", {})
        clicks.append({
          "timestamp": entry.get("timestamp"),
          "label": details.get("label"),
          "position": details.get("position"),
          "method": details.get("method")
        })
    return clicks

  def get_timeouts(self) -> List[Dict[str, Any]]:
    """타임아웃 이벤트 목록 반환"""
    timeouts = []
    for entry in self.entries:
      if entry.get("event_type") == "timeout":
        details = entry.get("details", {})
        timeouts.append({
          "timestamp": entry.get("timestamp"),
          "timeout_duration": details.get("timeout_duration"),
          "elapsed": details.get("elapsed")
        })
    return timeouts

  def count_by_template(self) -> Dict[str, int]:
    """템플릿별 감지 횟수 집계"""
    counts = defaultdict(int)
    for detection in self.get_detections():
      template = detection.get("template")
      if template:
        counts[template] += 1
    return dict(counts)

  def get_state_timeline(self) -> List[str]:
    """상태 전환 타임라인 반환"""
    timeline = []
    current_state = "START"
    timeline.append(f"0s: {current_state}")

    transitions = self.get_transitions()
    if not transitions:
      return timeline

    first_timestamp = datetime.fromisoformat(transitions[0]["timestamp"])
    for i, trans in enumerate(transitions):
      ts = datetime.fromisoformat(trans["timestamp"])
      elapsed = (ts - first_timestamp).total_seconds()
      timeline.append(f"{elapsed:.1f}s: {trans['from']} -> {trans['to']}")

    return timeline


def compare_logs(success_log: Path, failure_log: Path):
  """두 로그 파일 비교 및 리포트 생성"""
  print("=" * 70)
  print("자동화 실행 로그 비교 분석")
  print("=" * 70)
  print()

  # 로그 로드
  success = LogAnalyzer(success_log)
  failure = LogAnalyzer(failure_log)

  if not success.entries:
    print(f"[ERROR] {success_log}에서 로그를 읽을 수 없습니다")
    return

  if not failure.entries:
    print(f"[ERROR] {failure_log}에서 로그를 읽을 수 없습니다")
    return

  print(f"✓ 성공 로그: {success_log.name} ({len(success.entries)} 항목)")
  print(f"✗ 실패 로그: {failure_log.name} ({len(failure.entries)} 항목)")
  print()

  # 1. 상태 전환 비교
  print("[1] 상태 전환 타임라인 비교")
  print("-" * 70)
  print("\n✓ 성공한 실행:")
  for line in success.get_state_timeline():
    print(f"  {line}")

  print("\n✗ 실패한 실행:")
  for line in failure.get_state_timeline():
    print(f"  {line}")

  # 2. 템플릿 감지 비교
  print("\n" + "=" * 70)
  print("[2] 템플릿 감지 통계")
  print("-" * 70)

  success_detections = success.count_by_template()
  failure_detections = failure.count_by_template()

  all_templates = set(success_detections.keys()) | set(failure_detections.keys())
  for template in sorted(all_templates):
    s_count = success_detections.get(template, 0)
    f_count = failure_detections.get(template, 0)
    print(f"  {template:12} | 성공: {s_count:3}회  |  실패: {f_count:3}회", end="")
    if f_count > s_count:
      print(f"  ⚠️  ({f_count - s_count}회 더 많음)")
    else:
      print()

  # 3. 클릭 비교
  print("\n" + "=" * 70)
  print("[3] 클릭 이벤트 분석")
  print("-" * 70)

  success_clicks = success.get_clicks()
  failure_clicks = failure.get_clicks()

  print(f"\n성공: {len(success_clicks)}회 클릭")
  for click in success_clicks:
    print(f"  - {click['label']:20} at {click['position']}")

  print(f"\n실패: {len(failure_clicks)}회 클릭")
  for click in failure_clicks:
    print(f"  - {click['label']:20} at {click['position']}")

  # 4. 타임아웃 분석
  print("\n" + "=" * 70)
  print("[4] 타임아웃 분석")
  print("-" * 70)

  success_timeouts = success.get_timeouts()
  failure_timeouts = failure.get_timeouts()

  if success_timeouts:
    print(f"\n성공 중 타임아웃 발생: {len(success_timeouts)}회")
    for timeout in success_timeouts:
      elapsed = timeout.get("elapsed", 0)
      duration = timeout.get("timeout_duration", 0)
      print(f"  - {duration:.0f}초 제한 중 {elapsed:.1f}초 경과")

  if failure_timeouts:
    print(f"\n실패 중 타임아웃 발생: {len(failure_timeouts)}회")
    for timeout in failure_timeouts:
      elapsed = timeout.get("elapsed", 0)
      duration = timeout.get("timeout_duration", 0)
      print(f"  - {duration:.0f}초 제한 중 {elapsed:.1f}초 경과")

  if not success_timeouts and not failure_timeouts:
    print("\n타임아웃 없음")

  # 5. 개선 제안
  print("\n" + "=" * 70)
  print("[5] 개선 제안")
  print("-" * 70)
  print()

  suggestions = []

  # 템플릿별 제안
  for template in sorted(all_templates):
    f_count = failure_detections.get(template, 0)
    s_count = success_detections.get(template, 0)

    if f_count > s_count * 1.5:  # 실패에서 1.5배 이상 많이 감지 안 됨
      suggestions.append(
        f"• '{template}' 템플릿: 감지 실패율이 높습니다. "
        f"템플릿 품질을 점검하거나 CONFIDENCE 값을 조정해보세요."
      )

  # 상태 전환 제안
  success_transitions = len(success.get_transitions())
  failure_transitions = len(failure.get_transitions())

  if failure_transitions < success_transitions:
    missing = success_transitions - failure_transitions
    suggestions.append(
      f"• 상태 전환이 {missing}회 부족합니다. "
      f"특정 상태에서 멈추거나 오류가 발생했을 가능성이 있습니다."
    )

  if not suggestions:
    print("특별한 개선 사항이 없습니다. 현재 설정이 안정적입니다. ✓")
  else:
    for suggestion in suggestions:
      print(suggestion)

  print()
  print("=" * 70)


def main():
  if len(sys.argv) < 3:
    print("사용법: python compare_runs.py <성공_로그> <실패_로그>")
    print()
    print("예시:")
    print("  python compare_runs.py logs/run_20260225_100000.json logs/run_20260225_100500.json")
    print()
    print("또는 최근 로그 파일 자동 선택:")
    print("  python compare_runs.py --recent")
    sys.exit(1)

  if sys.argv[1] == "--recent":
    # 최근 로그 2개 자동 선택
    log_dir = Path("logs")
    if not log_dir.exists():
      print("[ERROR] logs 디렉토리가 없습니다")
      sys.exit(1)

    log_files = sorted(log_dir.glob("*.json"), reverse=True)[:2]
    if len(log_files) < 2:
      print(f"[ERROR] 최소 2개의 로그 파일이 필요합니다 (현재: {len(log_files)}개)")
      sys.exit(1)

    success_log = log_files[1]  # 더 오래된 것
    failure_log = log_files[0]  # 더 최신
  else:
    success_log = Path(sys.argv[1])
    failure_log = Path(sys.argv[2])

  compare_logs(success_log, failure_log)


if __name__ == "__main__":
  main()
