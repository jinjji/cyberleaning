#!/usr/bin/env python3
"""
최신 로그 분석 및 자동 진단 도구

runner.py 실행 후 자동화가 조용히 멈췄을 때,
최신 로그를 분석해 실패 원인과 설정값 조정을 제안합니다.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional


class DiagnosticsAnalyzer:
  """최신 로그 분석 및 진단"""

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

  def get_errors(self) -> List[Dict[str, Any]]:
    """에러 이벤트 목록"""
    errors = []
    for entry in self.entries:
      if entry.get("event_type") in ["error", "timeout"]:
        errors.append({
          "timestamp": entry.get("timestamp"),
          "type": entry.get("event_type"),
          "message": entry.get("message"),
          "details": entry.get("details", {})
        })
    return errors

  def get_last_state(self) -> Optional[str]:
    """마지막 상태 반환"""
    for entry in reversed(self.entries):
      if entry.get("event_type") == "state_transition":
        details = entry.get("details", {})
        return details.get("to")
    return None

  def get_state_sequence(self) -> List[str]:
    """상태 전환 시퀀스"""
    sequence = []
    for entry in self.entries:
      if entry.get("event_type") == "state_transition":
        details = entry.get("details", {})
        to_state = details.get("to")
        if to_state and (not sequence or sequence[-1] != to_state):
          sequence.append(to_state)
    return sequence

  def analyze_template_issues(self) -> List[str]:
    """템플릿 감지 문제 분석"""
    issues = []
    low_confidence_detections = []

    for entry in self.entries:
      if entry.get("event_type") == "detection":
        details = entry.get("details", {})
        template = details.get("template")
        hits = details.get("hits", 0)
        required = details.get("required_hits", 2)

        # 감지 실패 사례
        if hits < required:
          low_confidence_detections.append({
            "template": template,
            "hits": hits,
            "required": required
          })

    if low_confidence_detections:
      failed_templates = defaultdict(int)
      for det in low_confidence_detections:
        failed_templates[det["template"]] += 1

      issues.append("**템플릿 감지 문제:**")
      for template, count in sorted(failed_templates.items(), key=lambda x: -x[1]):
        issues.append(f"  - `{template}`: {count}회 감지 실패")
      issues.append(f"\n  → **권장사항**: `CONFIDENCE` 값을 낮추거나 ({[0.88, 0.85, 0.82]}), `REQUIRE_HITS` 조정 검토")

    return issues

  def analyze_timeout_issues(self) -> List[str]:
    """타임아웃 문제 분석"""
    issues = []
    timeout_by_state = defaultdict(int)

    for entry in self.entries:
      if entry.get("event_type") == "timeout":
        details = entry.get("details", {})
        state = details.get("state", "UNKNOWN")
        timeout_by_state[state] += 1

    if timeout_by_state:
      issues.append("**타임아웃 이슈:**")
      for state in sorted(timeout_by_state.keys()):
        count = timeout_by_state[state]
        issues.append(f"  - `{state}`: {count}회 타임아웃")

      # 상태별 권장사항
      recommendations = {
        "S0": "(`S0_TIMEOUT` 증가 권장, 기본값: 10.0초)",
        "S1": "(`S1_TIMEOUT` 확인, 필요시 증가)",
        "S2": "(`S2_TIMEOUT` 증가 권장, 기본값: 60.0초)",
        "S3": "(`S3_TIMEOUT` 증가 권장, 기본값: 5.0초)",
        "S4": "(`S4_TIMEOUT` 증가 권장, 기본값: 60.0초)"
      }

      issues.append("\n  → **권장사항:**")
      for state in sorted(timeout_by_state.keys()):
        if state in recommendations:
          issues.append(f"    - {state}: {recommendations[state]}")

    return issues

  def get_summary_recommendations(self) -> List[str]:
    """종합 권장사항"""
    recommendations = []
    last_state = self.get_last_state()
    state_sequence = self.get_state_sequence()
    errors = self.get_errors()

    recommendations.append("## 진단 요약\n")

    if last_state:
      recommendations.append(f"**마지막 상태**: `{last_state}`")
    else:
      recommendations.append("**마지막 상태**: 불명 (로그 부족)")

    recommendations.append(f"**상태 시퀀스**: {' → '.join(state_sequence) if state_sequence else 'N/A'}")
    recommendations.append(f"**에러/타임아웃 총 건수**: {len(errors)}")

    if len(errors) > 0:
      recommendations.append(f"\n최근 에러 (최대 3개):")
      for err in errors[-3:]:
        recommendations.append(f"  - [{err['type']}] {err['message']}")

    return recommendations

  def run(self):
    """진단 실행"""
    print(f"📋 로그 분석: {self.log_file.name}\n")

    # 요약
    summary = self.get_summary_recommendations()
    for line in summary:
      print(line)

    print()

    # 템플릿 문제
    template_issues = self.analyze_template_issues()
    if template_issues:
      for line in template_issues:
        print(line)
      print()

    # 타임아웃 문제
    timeout_issues = self.analyze_timeout_issues()
    if timeout_issues:
      for line in timeout_issues:
        print(line)
      print()

    # 권장 설정값
    print("## 현재 권장 설정값 (runner.py)\n")
    print("```python")
    print("CONFIDENCE = 0.85  # 기본값: 0.88")
    print("REQUIRE_HITS = 1   # 기본값: 2")
    print("S0_TIMEOUT = 15.0  # 기본값: 10.0")
    print("S2_TIMEOUT = 90.0  # 기본값: 60.0")
    print("S3_TIMEOUT = 10.0  # 기본값: 5.0")
    print("S4_TIMEOUT = 90.0  # 기본값: 60.0")
    print("```\n")

    if not template_issues and not timeout_issues:
      print("✅ 특별한 이슈가 감지되지 않았습니다. 자동화가 정상 작동 중입니다.")


def get_latest_log() -> Optional[Path]:
  """가장 최근 로그 파일 반환"""
  log_dir = Path("logs")
  if not log_dir.exists():
    return None

  json_files = sorted(log_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
  return json_files[0] if json_files else None


def main():
  latest = get_latest_log()
  if not latest:
    print("❌ 로그 파일이 없습니다. /run 으로 먼저 자동화를 실행하세요.")
    sys.exit(1)

  analyzer = DiagnosticsAnalyzer(latest)
  analyzer.run()


if __name__ == "__main__":
  main()
