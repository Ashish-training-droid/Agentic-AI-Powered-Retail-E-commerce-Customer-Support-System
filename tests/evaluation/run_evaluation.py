"""
End-to-end evaluation runner (Rohan (Person 5)).

Loads every case from ``test_cases.json``, runs each through the compiled
LangGraph pipeline, and writes a structured result file. Designed to run
deterministically in mock mode (``USE_MOCK=true``) so we get a stable
pre-/post-Person-3 baseline.

Usage::

    # one-shot full eval
    USE_MOCK=true python -m tests.evaluation.run_evaluation

    # write to a different snapshot file
    python -m tests.evaluation.run_evaluation --output tests/evaluation/report_v2.json

    # run a single case for debugging
    python -m tests.evaluation.run_evaluation --only TC_011

The output JSON is consumed by ``evaluation_report.py`` for the per-metric
summary used in the final presentation.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.orchestrator.graph import app
from src.utils.session import build_initial_state

CASES_PATH = Path(__file__).parent / "test_cases.json"
DEFAULT_RESULTS_PATH = Path(__file__).parent / "report_v1.json"


# ---------------------------------------------------------------------------
# Expectation matchers
# ---------------------------------------------------------------------------
def _bool(value: Any) -> bool:
    return bool(value)


def _str_lower(value: Any) -> str:
    return str(value or "").lower()


def _check_case(case: dict, output: dict) -> dict[str, Any]:
    """Compare one case's expectations against the actual output."""
    expected = case.get("expected", {})
    issues: list[str] = []
    matches: list[str] = []

    intent = _str_lower(output.get("intent"))
    sentiment = _str_lower(output.get("sentiment"))
    risk_band = _str_lower(output.get("risk_band") or "auto")
    escalation = _bool(output.get("escalation_required"))
    approval = _str_lower(output.get("risk_band")) == "approval_required" or _bool(output.get("requires_human_approval"))
    clarify_called = "clarification_handler" in (output.get("agents_called") or [])
    response_text = (output.get("response_text") or "").lower()
    priority = _str_lower(output.get("priority"))
    target_team = _str_lower(output.get("target_team"))
    references = [r.lower() for r in (output.get("references_cited") or [])]
    intent_conf = float(output.get("intent_confidence") or 0.0)

    if "intent" in expected:
        target = _str_lower(expected["intent"])
        if intent == target:
            matches.append(f"intent={intent}")
        else:
            issues.append(f"intent expected={target} actual={intent}")

    if "sentiment_should_be_any" in expected:
        choices = {_str_lower(s) for s in expected["sentiment_should_be_any"]}
        if sentiment in choices:
            matches.append(f"sentiment={sentiment}")
        else:
            issues.append(f"sentiment expected_one_of={sorted(choices)} actual={sentiment}")

    if "escalation" in expected:
        target = _bool(expected["escalation"])
        if escalation == target:
            matches.append(f"escalation={escalation}")
        else:
            issues.append(f"escalation expected={target} actual={escalation}")

    if expected.get("escalation_or_approval"):
        if escalation or approval:
            matches.append("escalation_or_approval=True")
        else:
            issues.append("expected escalation OR approval_required, got auto")

    if expected.get("escalation_or_approval_or_clarify"):
        if escalation or approval or clarify_called:
            matches.append("escalation_or_approval_or_clarify=True")
        else:
            issues.append("expected escalation/approval/clarify, got auto")

    if expected.get("should_clarify"):
        if clarify_called:
            matches.append("clarification_called")
        else:
            issues.append("expected clarification, none triggered")

    if expected.get("should_clarify_or_handle"):
        if clarify_called or output.get("response_text"):
            matches.append("clarified_or_handled")
        else:
            issues.append("no response text and no clarification")

    if "risk_band" in expected:
        target = _str_lower(expected["risk_band"])
        if risk_band == target:
            matches.append(f"risk_band={risk_band}")
        else:
            issues.append(f"risk_band expected={target} actual={risk_band}")

    if "min_confidence" in expected:
        threshold = float(expected["min_confidence"])
        if intent_conf >= threshold:
            matches.append(f"intent_confidence>={threshold}")
        else:
            issues.append(f"intent_confidence expected>={threshold} actual={intent_conf:.2f}")

    if "min_priority" in expected and priority:
        # P1 < P2 < P3 < P4 (lower number = higher urgency)
        target_num = int(_str_lower(expected["min_priority"]).replace("p", "") or 4)
        actual_num = int(priority.replace("p", "") or 4)
        if actual_num <= target_num:
            matches.append(f"priority<={expected['min_priority']}")
        else:
            issues.append(f"priority expected<={expected['min_priority']} actual={priority.upper()}")

    if "should_route_team_any" in expected and target_team:
        choices = {_str_lower(t) for t in expected["should_route_team_any"]}
        if target_team in choices:
            matches.append(f"team={target_team}")
        else:
            issues.append(f"team expected_one_of={sorted(choices)} actual={target_team}")

    if expected.get("should_have_policy_refs"):
        if output.get("policy_snippets") or references:
            matches.append("policy_refs_present")
        else:
            issues.append("expected policy refs, none returned")

    if "should_contain_any" in expected:
        needles = [s.lower() for s in expected["should_contain_any"]]
        if any(needle in response_text for needle in needles):
            matches.append("response_contains_expected")
        else:
            issues.append(f"response missing all of {needles}")

    if "must_not_contain_any" in expected:
        forbidden = [s.lower() for s in expected["must_not_contain_any"]]
        leaks = [s for s in forbidden if s in response_text]
        if not leaks:
            matches.append("response_clean_of_forbidden")
        else:
            issues.append(f"response leaked forbidden tokens: {leaks}")

    passed = len(issues) == 0
    return {
        "passed": passed,
        "matches": matches,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def _run_one(case: dict) -> dict[str, Any]:
    state = build_initial_state(
        message=case.get("message", ""),
        customer_id=case.get("customer_id", ""),
        channel=case.get("channel", "web"),
    )
    start = time.perf_counter()
    try:
        output = app.invoke(state)
        error = None
    except Exception as exc:  # pragma: no cover — exercised in error tests
        output = {}
        error = f"{type(exc).__name__}: {exc}"
    latency_ms = (time.perf_counter() - start) * 1000.0

    evaluation = _check_case(case, output)
    return {
        "id": case["id"],
        "category": case.get("category", "uncategorized"),
        "message": case.get("message", ""),
        "expected": case.get("expected", {}),
        "actual": {
            "intent": output.get("intent"),
            "intent_confidence": output.get("intent_confidence"),
            "sentiment": output.get("sentiment"),
            "urgency": output.get("urgency"),
            "risk_score": output.get("risk_score"),
            "risk_band": output.get("risk_band"),
            "escalation_required": output.get("escalation_required"),
            "requires_human_approval": output.get("requires_human_approval"),
            "target_team": output.get("target_team"),
            "priority": output.get("priority"),
            "sla_target": output.get("sla_target"),
            "response_confidence": output.get("response_confidence"),
            "references_cited": output.get("references_cited"),
            "agents_called": output.get("agents_called"),
            "quality_score": output.get("quality_score"),
            "quality_issues": output.get("quality_issues"),
            "response_text": output.get("response_text"),
        },
        "evaluation": evaluation,
        "latency_ms": round(latency_ms, 2),
        "error": error,
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _aggregate(results: list[dict]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {"total": 0}

    passed = sum(1 for r in results if r["evaluation"]["passed"])
    errors = sum(1 for r in results if r["error"])
    avg_latency = round(sum(r["latency_ms"] for r in results) / total, 2)

    escalations = sum(1 for r in results if r["actual"].get("escalation_required"))
    approvals = sum(1 for r in results if _str_lower(r["actual"].get("risk_band")) == "approval_required")
    auto = sum(1 for r in results if _str_lower(r["actual"].get("risk_band")) == "auto")

    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_category.setdefault(r["category"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        if r["evaluation"]["passed"]:
            bucket["passed"] += 1

    intent_dist = Counter(r["actual"].get("intent") for r in results)
    intent_matches = sum(
        1 for r in results
        if "intent" in r["expected"]
        and _str_lower(r["expected"]["intent"]) == _str_lower(r["actual"].get("intent"))
    )
    intent_eligible = sum(1 for r in results if "intent" in r["expected"])

    # Escalation precision / recall against the cases that declared an
    # explicit "escalation" expectation.
    eligible_for_escalation_eval = [r for r in results if "escalation" in r["expected"]]
    true_positive = sum(
        1 for r in eligible_for_escalation_eval
        if r["expected"]["escalation"] and r["actual"].get("escalation_required")
    )
    false_positive = sum(
        1 for r in eligible_for_escalation_eval
        if not r["expected"]["escalation"] and r["actual"].get("escalation_required")
    )
    false_negative = sum(
        1 for r in eligible_for_escalation_eval
        if r["expected"]["escalation"] and not r["actual"].get("escalation_required")
    )
    precision = round(true_positive / (true_positive + false_positive), 4) if (true_positive + false_positive) else 1.0
    recall = round(true_positive / (true_positive + false_negative), 4) if (true_positive + false_negative) else 1.0

    avg_quality = round(
        sum(float(r["actual"].get("quality_score") or 0.0) for r in results) / total, 4
    )
    avg_confidence = round(
        sum(float(r["actual"].get("response_confidence") or 0.0) for r in results) / total, 4
    )

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4),
        "errors": errors,
        "avg_latency_ms": avg_latency,
        "avg_quality_score": avg_quality,
        "avg_response_confidence": avg_confidence,
        "intent_accuracy": round(intent_matches / intent_eligible, 4) if intent_eligible else None,
        "escalation_precision": precision,
        "escalation_recall": recall,
        "false_escalation_rate": round(false_positive / max(len(eligible_for_escalation_eval), 1), 4),
        "by_category": by_category,
        "band_distribution": {
            "auto": auto,
            "approval_required": approvals,
            "escalate": escalations,
        },
        "intent_distribution": dict(intent_dist.most_common()),
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def run_evaluation(
    cases_path: Path = CASES_PATH,
    output_path: Path = DEFAULT_RESULTS_PATH,
    only: str | None = None,
) -> dict[str, Any]:
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = payload["cases"] if "cases" in payload else payload

    if only:
        cases = [c for c in cases if c["id"] == only]
        if not cases:
            raise SystemExit(f"No test case with id={only}")

    results = [_run_one(case) for case in cases]
    summary = _aggregate(results)
    snapshot = {
        "cases_file": str(cases_path),
        "use_mock": os.getenv("USE_MOCK", "false"),
        "summary": summary,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    _print_summary(snapshot)
    return snapshot


def _print_summary(snapshot: dict) -> None:
    summary = snapshot["summary"]
    print()
    print("=" * 70)
    print("  Evaluation Summary")
    print("=" * 70)
    print(f"  Total cases       : {summary['total']}")
    print(f"  Passed            : {summary['passed']}  ({summary['pass_rate']:.0%})")
    print(f"  Failed            : {summary['failed']}")
    print(f"  Errors            : {summary['errors']}")
    print(f"  Avg latency       : {summary['avg_latency_ms']} ms")
    print(f"  Avg quality score : {summary['avg_quality_score']}")
    print(f"  Avg resp. conf.   : {summary['avg_response_confidence']}")
    if summary.get("intent_accuracy") is not None:
        print(f"  Intent accuracy   : {summary['intent_accuracy']:.0%}")
    print(f"  Escalation P / R  : {summary['escalation_precision']:.0%} / {summary['escalation_recall']:.0%}")
    print(f"  False escalation  : {summary['false_escalation_rate']:.0%}")
    print()
    print("  By category:")
    for cat, bucket in summary["by_category"].items():
        rate = bucket["passed"] / bucket["total"] if bucket["total"] else 0
        print(f"    {cat:<14} {bucket['passed']}/{bucket['total']}  ({rate:.0%})")
    print()
    print("  Band distribution:")
    for band, count in summary["band_distribution"].items():
        print(f"    {band:<20} {count}")
    print()
    failing = [r for r in snapshot["results"] if not r["evaluation"]["passed"]]
    if failing:
        print(f"  Failing cases ({len(failing)}):")
        for r in failing:
            print(f"    {r['id']:<8} [{r['category']}] {r['message'][:60]}")
            for issue in r["evaluation"]["issues"]:
                print(f"        -> {issue}")
    print("=" * 70)


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Rohan (Person 5) evaluation harness.")
    parser.add_argument("--cases", type=Path, default=CASES_PATH, help="Path to test_cases.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS_PATH, help="Where to write the snapshot")
    parser.add_argument("--only", type=str, default=None, help="Run only the case with this id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_cli().parse_args(argv)
    snapshot = run_evaluation(args.cases, args.output, args.only)
    return 0 if snapshot["summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
