"""
Perturbation generator for evaluation cases (Person 5).

Takes the routine cases from ``test_cases.json`` and mutates each one into
a "near miss" — typo, missing order ID, whitespace pollution, case change
— so we can assert graceful degradation without writing 100 more cases by
hand.

For every mutated case we assert one of:
    * the pipeline still resolved to the same intent + did not escalate, OR
    * the pipeline asked for clarification / requested an order ID.

Anything else is a silent regression and gets reported.

Usage::

    python -m tests.evaluation.perturbations
    python -m tests.evaluation.perturbations --output tests/evaluation/perturbation_report.md
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path
from typing import Callable

from src.orchestrator.graph import app
from src.utils.session import build_initial_state

CASES_PATH = Path(__file__).parent / "test_cases.json"
DEFAULT_OUTPUT = Path(__file__).parent / "perturbation_report.md"

random.seed(42)


# ---------------------------------------------------------------------------
# Mutators
# ---------------------------------------------------------------------------
def _typo(message: str) -> str:
    if len(message) < 6:
        return message + " plz"
    idx = random.randint(2, len(message) - 3)
    return message[:idx] + message[idx + 1] + message[idx] + message[idx + 2:]


def _strip_order_id(message: str) -> str:
    return re.sub(r"\bSE\d{4,6}\b", "", message, flags=re.IGNORECASE).strip() or message


def _uppercase(message: str) -> str:
    return message.upper()


def _add_whitespace_noise(message: str) -> str:
    return "  " + "  ".join(message.split()) + "  "


def _add_filler(message: str) -> str:
    return f"hey there um {message} thanks!!"


def _truncate(message: str) -> str:
    if len(message) <= 12:
        return message[:6]
    return message[: max(8, len(message) // 3)]


def _mix_language(message: str) -> str:
    return f"{message} (kya yeh sahi hai?)"


MUTATORS: list[tuple[str, Callable[[str], str]]] = [
    ("typo", _typo),
    ("strip_order_id", _strip_order_id),
    ("uppercase", _uppercase),
    ("whitespace", _add_whitespace_noise),
    ("filler", _add_filler),
    ("truncate", _truncate),
    ("mix_language", _mix_language),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def _run_mutated(base_case: dict, mutator_name: str, mutator: Callable[[str], str]) -> dict:
    original_message = base_case["message"]
    mutated_message = mutator(original_message)
    state = build_initial_state(
        message=mutated_message,
        customer_id=base_case.get("customer_id", ""),
        channel=base_case.get("channel", "web"),
    )
    start = time.perf_counter()
    try:
        output = app.invoke(state)
        error = None
    except Exception as exc:  # pragma: no cover
        output = {}
        error = f"{type(exc).__name__}: {exc}"
    latency_ms = (time.perf_counter() - start) * 1000.0

    expected_intent = (base_case.get("expected") or {}).get("intent")
    actual_intent = output.get("intent")
    escalated = bool(output.get("escalation_required"))
    approval = (output.get("risk_band") or "auto") == "approval_required"
    clarified = "clarification_handler" in (output.get("agents_called") or [])

    # Pass conditions:
    #   1. same intent + did not falsely escalate
    #   2. or pipeline asked for clarification / approval / escalation
    intent_match = (expected_intent is None) or (str(actual_intent or "").lower() == str(expected_intent).lower())
    graceful = clarified or approval or escalated
    passed = (intent_match and not escalated) or graceful

    return {
        "base_id": base_case["id"],
        "mutator": mutator_name,
        "original_message": original_message,
        "mutated_message": mutated_message,
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "escalation_required": escalated,
        "approval_required": approval,
        "clarified": clarified,
        "passed": passed,
        "latency_ms": round(latency_ms, 2),
        "error": error,
    }


def run_perturbations(cases_path: Path = CASES_PATH) -> dict:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = payload["cases"] if "cases" in payload else payload
    routine_cases = [c for c in cases if c.get("category") == "routine"]

    results: list[dict] = []
    for case in routine_cases:
        for mutator_name, mutator in MUTATORS:
            results.append(_run_mutated(case, mutator_name, mutator))

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    summary = {
        "base_cases": len(routine_cases),
        "mutators": len(MUTATORS),
        "total_perturbations": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 1.0,
    }
    return {"summary": summary, "results": results}


def render_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Perturbation Report",
        "",
        f"- Base cases: {s['base_cases']}",
        f"- Mutators applied: {s['mutators']}",
        f"- Total perturbations: {s['total_perturbations']}",
        f"- Pass rate: {s['pass_rate']:.0%}  ({s['passed']}/{s['total_perturbations']})",
        "",
        "## Failures",
        "",
    ]
    failing = [r for r in report["results"] if not r["passed"]]
    if not failing:
        lines.append("_No failures — pipeline degrades gracefully across all mutators._")
    for r in failing:
        lines.append(f"### {r['base_id']} / {r['mutator']}")
        lines.append("")
        lines.append(f"- original : `{r['original_message']}`")
        lines.append(f"- mutated  : `{r['mutated_message']}`")
        lines.append(f"- expected_intent : `{r['expected_intent']}`")
        lines.append(f"- actual_intent   : `{r['actual_intent']}`")
        lines.append(f"- escalated={r['escalation_required']} approval={r['approval_required']} clarified={r['clarified']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run perturbation tests on routine cases.")
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    report = run_perturbations(args.cases)
    md = render_markdown(report)
    args.output.write_text(md, encoding="utf-8")
    print(md)
    print(f"\nWrote perturbation report to {args.output}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
