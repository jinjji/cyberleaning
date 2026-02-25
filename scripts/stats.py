#!/usr/bin/env python3
"""
전체 로그 통계 분석 도구

logs/ 폴더의 모든 JSON 로그를 분석하여:
- 자동화 성공률
- 평균 사이클 시간
- 상태별 체류 시간
- 타임아웃/에러 빈도
등을 통계로 출력합니다.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple


class StatsAnalyzer:
  """전체 로그 통계 분석"""

  def __init__(self):
    self.log_dir = Path("logs")
    self.all_entries = []
    self.load_all()

  def load_all(self):
    """모든 JSON 로그 파일 로드"""
    if not self.log_dir.exists():
      print(f"[ERROR] 로그 디렉토리가 없습니다: {self.log_dir}")
      return

    json_files = sorted(self.log_dir.glob("*.json"))
    if not json_files:
      print(f"[ERROR] 로그 파일이 없습니다: {self.log_dir}")
      return

    print(f"📂 {len(json_files)}개 로그 파일 로딩 중...")

    for log_file in json_files:
      with open(log_file, "r") as f:
        for line in f:
          try:
            entry = json.loads(line.strip())
            entry["_file"] = log_file.name
            self.all_entries.append(entry)
          except json.JSONDecodeError:
            pass

  def get_transitions(self) -> List[Dict[str, Any]]:
    """전체 상태 전환 목록"""
    transitions = []
    for entry in self.all_entries:
      if entry.get("event_type") == "state_transition":
        details = entry.get("details", {})
        transitions.append({
          "timestamp": entry.get("timestamp"),
          "file": entry.get("_file"),
          "from": details.get("from"),
          "to": details.get("to"),
          "reason": details.get("reason")
        })
    return transitions

  def count_complete_cycles(self) -> int:
    """완전한 사이클 (S0→S1→S2→S3→S4→S0) 횟수"""
    transitions = self.get_transitions()
    cycle_count = 0
    expected_sequence = ["S1", "S2", "S3", "S4", "S0"]
    current_sequence = []

    for trans in transitions:
      current_sequence.append(trans["to"])

      if current_sequence == expected_sequence:
        cycle_count += 1
        current_sequence = []

    return cycle_count

  def analyze_state_durations(self) -> Dict[str, Dict[str, float]]:
    """상태별 체류 시간 분석 (평균, 최소, 최대)"""
    transitions = self.get_transitions()

    if not transitions:
      return {}

    state_durations = defaultdict(list)

    for i in range(len(transitions) - 1):
      current = transitions[i]
      next_trans = transitions[i + 1]

      # 같은 파일 내에서만 계산
      if current["file"] != next_trans["file"]:
        continue

      try:
        current_time = datetime.fromisoformat(current["timestamp"])
        next_time = datetime.fromisoformat(next_trans["timestamp"])
        duration = (next_time - current_time).total_seconds()

        state = current["to"]
        if duration > 0:  # 음수 지속시간 제외
          state_durations[state].append(duration)
      except (ValueError, TypeError):
        pass

    # 통계 계산
    result = {}
    for state, durations in sorted(state_durations.items()):
      if durations:
        result[state] = {
          "avg": sum(durations) / len(durations),
          "min": min(durations),
          "max": max(durations),
          "count": len(durations)
        }

    return result

  def count_errors_and_timeouts(self) -> Dict[str, int]:
    """에러 및 타임아웃 빈도"""
    error_types = defaultdict(int)

    for entry in self.all_entries:
      if entry.get("event_type") in ["error", "timeout"]:
        details = entry.get("details", {})
        error_key = f"{entry.get('event_type')}"
        if "state" in details:
          error_key += f":{details['state']}"
        error_types[error_key] += 1

    return dict(error_types)

  def get_file_summary(self) -> Dict[str, Dict[str, Any]]:
    """파일별 요약 (실행 횟수, 성공률, 마지막 상태)"""
    file_stats = defaultdict(lambda: {
      "total_events": 0,
      "errors": 0,
      "timeouts": 0,
      "last_state": None,
      "last_time": None
    })

    for entry in self.all_entries:
      file_name = entry.get("_file")
      if not file_name:
        continue

      file_stats[file_name]["total_events"] += 1

      if entry.get("event_type") == "error":
        file_stats[file_name]["errors"] += 1
      elif entry.get("event_type") == "timeout":
        file_stats[file_name]["timeouts"] += 1
      elif entry.get("event_type") == "state_transition":
        details = entry.get("details", {})
        file_stats[file_name]["last_state"] = details.get("to")
        file_stats[file_name]["last_time"] = entry.get("timestamp")

    return dict(file_stats)

  def print_summary(self):
    """전체 요약 출력"""
    transitions = self.get_transitions()
    complete_cycles = self.count_complete_cycles()
    state_durations = self.analyze_state_durations()
    errors_timeouts = self.count_errors_and_timeouts()
    file_summary = self.get_file_summary()

    print(f"\n## 📊 전체 통계\n")

    print(f"**로그 파일 수**: {len(file_summary)}")
    print(f"**전체 이벤트**: {len(self.all_entries)}")
    print(f"**상태 전환**: {len(transitions)}")
    print(f"**완전한 사이클 (S0→S1→S2→S3→S4→S0)**: {complete_cycles}")

    if len(transitions) > 0:
      avg_cycle_time = sum(
        (datetime.fromisoformat(transitions[i + 1]["timestamp"]) -
         datetime.fromisoformat(transitions[i]["timestamp"])).total_seconds()
        for i in range(len(transitions) - 1)
        if transitions[i]["file"] == transitions[i + 1]["file"]
      ) / max(1, len(transitions) - 1)
      print(f"**평균 전환 시간**: {avg_cycle_time:.2f}초")

    print(f"\n## ⏱️  상태별 체류 시간\n")

    if state_durations:
      print("| 상태 | 평균(초) | 최소(초) | 최대(초) | 횟수 |")
      print("|------|----------|----------|----------|------|")
      for state in sorted(state_durations.keys()):
        stats = state_durations[state]
        print(f"| `{state}` | {stats['avg']:.2f} | {stats['min']:.2f} | {stats['max']:.2f} | {stats['count']} |")
    else:
      print("(데이터 없음)")

    print(f"\n## ⚠️  에러 및 타임아웃 통계\n")

    if errors_timeouts:
      print("| 유형 | 발생 횟수 |")
      print("|------|----------|")
      for error_type in sorted(errors_timeouts.keys()):
        count = errors_timeouts[error_type]
        print(f"| `{error_type}` | {count} |")
    else:
      print("(에러/타임아웃 없음)")

    print(f"\n## 📁 파일별 요약\n")

    if file_summary:
      print("| 파일명 | 이벤트 | 에러 | 타임아웃 | 마지막 상태 |")
      print("|--------|--------|------|----------|------------|")
      for file_name in sorted(file_summary.keys()):
        stats = file_summary[file_name]
        last_state = stats["last_state"] or "N/A"
        print(f"| `{file_name}` | {stats['total_events']} | {stats['errors']} | {stats['timeouts']} | `{last_state}` |")
    else:
      print("(데이터 없음)")

    print()


def main():
  if not Path("logs").exists():
    print("❌ logs 디렉토리가 없습니다. /run 으로 먼저 자동화를 실행하세요.")
    sys.exit(1)

  analyzer = StatsAnalyzer()

  if not analyzer.all_entries:
    print("❌ 분석할 로그가 없습니다.")
    sys.exit(1)

  analyzer.print_summary()
  print("✅ 통계 분석 완료")


if __name__ == "__main__":
  main()
