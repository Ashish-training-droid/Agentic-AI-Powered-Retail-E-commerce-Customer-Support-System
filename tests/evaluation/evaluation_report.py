"""
Standalone report generator for the evaluation harness (Person 5).

Reads a snapshot produced by ``run_evaluation.py`` and prints / writes a
markdown report suitable for dropping into slides 15-16 of the deck.

Usage::

    python -m tests.evaluation.evaluation_report
    python -m tests.evaluation.evaluation_report --input report_v1.json --output report_v1.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path(__file__).parent / "report_v1.json"
DEFAULT_OUTPUT = Path(__file__).parent / "report_v1.md"


def render_markdown(snapshot: dict[str, Any]) -> str:
    s = snapshot["summary"]
    lines: list[str] = []
    lines.append("# ShopEase Agentic AI — Evaluation Report")
    lines.append("")
    lines.append(f"- Cases file: `{snapshot.get('cases_file', 'tests/evaluation/test_cases.json')}`")
    lines.append(f"- USE_MOCK: `{snapshot.get('use_mock', 'unknown')}`")
    lines.append("")
    lines.append("## Headline metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total cases | {s['total']} |")
    lines.append(f"| Pass rate | {s['pass_rate']:.0%} ({s['passed']}/{s['total']}) |")
    lines.append(f"| Errors | {s['errors']} |")
    lines.append(f"| Intent accuracy | {(s['intent_accuracy'] or 0):.0%} |")
    lines.append(f"| Escalation precision | {s['escalation_precision']:.0%} |")
    lines.append(f"| Escalation recall | {s['escalation_recall']:.0%} |")
    lines.append(f"| False escalation rate | {s['false_escalation_rate']:.0%} |")
    lines.append(f"| Avg quality score | {s['avg_quality_score']:.2f} |")
    lines.append(f"| Avg response confidence | {s['avg_response_confidence']:.2f} |")
    lines.append(f"| Avg latency (ms) | {s['avg_latency_ms']} |")
    lines.append("")
    lines.append("## Pass rate by category")
    lines.append("")
    lines.append("| Category | Passed | Total | Rate |")
    lines.append("|----------|-------:|------:|-----:|")
    for cat, bucket in s["by_category"].items():
        rate = bucket["passed"] / bucket["total"] if bucket["total"] else 0
        lines.append(f"| {cat} | {bucket['passed']} | {bucket['total']} | {rate:.0%} |")
    lines.append("")
    lines.append("## Risk band distribution")
    lines.append("")
    lines.append("| Band | Count |")
    lines.append("|------|------:|")
    for band, count in s["band_distribution"].items():
        lines.append(f"| {band} | {count} |")
    lines.append("")
    lines.append("## Intent distribution (actual classifications)")
    lines.append("")
    lines.append("| Intent | Count |")
    lines.append("|--------|------:|")
    for intent, count in s["intent_distribution"].items():
        lines.append(f"| {intent or 'unknown'} | {count} |")
    lines.append("")
    failing = [r for r in snapshot["results"] if not r["evaluation"]["passed"]]
    lines.append(f"## Failing cases ({len(failing)})")
    lines.append("")
    if not failing:
        lines.append("_No failing cases — congrats._")
    for r in failing:
        lines.append(f"### {r['id']} ({r['category']})")
        lines.append("")
        lines.append(f"**Message:** {r['message']}")
        lines.append("")
        lines.append(f"**Expected:** `{json.dumps(r['expected'])}`")
        lines.append(f"**Actual intent:** `{r['actual'].get('intent')}`  /  "
                     f"**band:** `{r['actual'].get('risk_band')}`  /  "
                     f"**team:** `{r['actual'].get('target_team') or '-'}`")
        lines.append("")
        for issue in r["evaluation"]["issues"]:
            lines.append(f"- {issue}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the evaluation snapshot as markdown.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not args.input.exists():
        raise SystemExit(f"Snapshot not found at {args.input}. Run run_evaluation first.")

    snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    md = render_markdown(snapshot)
    args.output.write_text(md, encoding="utf-8")
    print(md)
    print(f"\nWrote report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
