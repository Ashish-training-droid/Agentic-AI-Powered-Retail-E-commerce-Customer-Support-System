"""
Tests for the Escalation & Risk Agent (Rohan (Person 5)).

Strategy
--------
Every test builds its own minimal ``AgentState`` from
``tests.fixtures.order_contexts`` so we never depend on Pallavi (Person 3)'s runtime
implementation. The risk agent's contract is the schema, not the source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.agents.escalation_risk import (
    ESCALATE_THRESHOLD,
    ESCALATION_ROUTES,
    FLAG_THRESHOLD,
    WEIGHTS,
    calculate_risk_factors,
    calculate_risk_score,
    check_risk,
)
from tests.fixtures.order_contexts import (
    angry_repeated_contact,
    damaged_low_value,
    damaged_vip_high_value,
    delivered_no_issue,
    empty_context,
    fraud_signal_duplicate_refund,
    lost_high_value_shipment,
    payment_disputed_card,
    regular_in_transit,
    vip_high_value_in_transit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _state(
    *,
    intent: str = "general_faq",
    sentiment: str = "neutral",
    confidence: float = 0.9,
    order_context: dict | None = None,
    policy_snippets: list | None = None,
    customer_tier: str | None = None,
) -> dict[str, Any]:
    """Build a minimal AgentState-shaped dict for the risk agent."""
    ctx = order_context if order_context is not None else {}
    state: dict[str, Any] = {
        "intent": intent,
        "sentiment": sentiment,
        "intent_confidence": confidence,
        "order_context": ctx,
        "policy_snippets": policy_snippets or [],
    }
    if customer_tier is not None:
        state["customer_tier"] = customer_tier
    return state


# ---------------------------------------------------------------------------
# Sanity / configuration tests
# ---------------------------------------------------------------------------
def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_thresholds_are_ordered():
    assert 0.0 < FLAG_THRESHOLD < ESCALATE_THRESHOLD <= 1.0


def test_every_route_has_team_and_priority():
    for code, route in ESCALATION_ROUTES.items():
        assert route.team, f"route {code} missing team"
        assert route.priority.startswith("P"), f"route {code} bad priority {route.priority}"
        assert route.sla_hours > 0, f"route {code} missing SLA"
        assert route.severity > 0, f"route {code} missing severity"


# ---------------------------------------------------------------------------
# Per-factor unit tests (only one factor non-zero per test)
# ---------------------------------------------------------------------------
def test_factor_sentiment_angry_dominates():
    factors = {f.name: f for f in calculate_risk_factors(_state(sentiment="angry"))}
    assert factors["sentiment"].raw == 0.8
    assert factors["sentiment"].contribution == round(0.8 * WEIGHTS["sentiment"], 4)


def test_factor_order_value_high():
    factors = {f.name: f for f in calculate_risk_factors(_state(order_context=vip_high_value_in_transit()))}
    assert factors["order_value"].raw == 0.8


def test_factor_order_value_zero_when_no_context():
    factors = {f.name: f for f in calculate_risk_factors(_state(order_context=empty_context()))}
    assert factors["order_value"].raw == 0.0
    assert factors["customer_tier"].raw == 0.0


def test_factor_intent_confidence_low_pushes_risk():
    factors = {f.name: f for f in calculate_risk_factors(_state(confidence=0.2))}
    assert factors["intent_confidence"].raw == 1.0


def test_factor_customer_tier_vip():
    factors = {f.name: f for f in calculate_risk_factors(_state(customer_tier="vip"))}
    assert factors["customer_tier"].raw == 0.6


def test_factor_repeated_contact_above_threshold():
    # angry_repeated_contact() has 4 CRM notes which meets REPEATED_CONTACT_HIGH (4).
    factors = {f.name: f for f in calculate_risk_factors(_state(order_context=angry_repeated_contact()))}
    assert factors["repeated_contact"].raw == 1.0


def test_factor_issue_severity_damaged_product():
    factors = {f.name: f for f in calculate_risk_factors(_state(intent="damaged_product"))}
    assert factors["issue_severity"].raw == 1.0


def test_factor_issue_severity_product_inquiry_is_safe():
    factors = {f.name: f for f in calculate_risk_factors(_state(intent="product_inquiry"))}
    assert factors["issue_severity"].raw == 0.0


# ---------------------------------------------------------------------------
# Composite score sanity
# ---------------------------------------------------------------------------
def test_composite_score_in_bounds():
    score = calculate_risk_score(_state(sentiment="angry", confidence=0.1,
                                        order_context=vip_high_value_in_transit(),
                                        customer_tier="vip"))
    assert 0.0 <= score <= 1.0


def test_baseline_routine_case_is_low_risk():
    score = calculate_risk_score(
        _state(intent="order_tracking", sentiment="neutral", confidence=0.95,
               order_context=regular_in_transit())
    )
    assert score < FLAG_THRESHOLD


# ---------------------------------------------------------------------------
# Per-route routing tests (one per escalation route)
# ---------------------------------------------------------------------------
def test_route_fraud_via_duplicate_refunds():
    out = check_risk(_state(intent="refund_status", order_context=fraud_signal_duplicate_refund()))
    assert out["target_team"] == "fraud_review"
    assert out["priority"] == "P1"
    assert out["risk_band"] == "escalate"


def test_route_payment_dispute():
    out = check_risk(_state(intent="refund_status", order_context=payment_disputed_card()))
    assert out["target_team"] == "refund_specialist"
    assert out["priority"] == "P2"


def test_route_angry_high_value_is_p1():
    out = check_risk(_state(intent="return_request", sentiment="angry",
                            order_context=damaged_vip_high_value(),
                            customer_tier="vip", policy_snippets=[{}]))
    assert out["priority"] == "P1"
    assert out["risk_band"] == "escalate"


def test_route_damaged_high_value_when_not_angry():
    out = check_risk(_state(intent="damaged_product", sentiment="neutral",
                            order_context=damaged_vip_high_value(), customer_tier="vip",
                            policy_snippets=[{}]))
    assert out["target_team"] in {"replacement_team", "senior_agent"}
    assert out["priority"] in {"P1", "P2"}


def test_route_lost_shipment():
    out = check_risk(_state(intent="delivery_complaint", order_context=lost_high_value_shipment()))
    assert out["target_team"] == "logistics"
    assert out["priority"] == "P2"


def test_route_vip_attention():
    out = check_risk(_state(intent="return_request", sentiment="neutral", confidence=0.9,
                            order_context=vip_high_value_in_transit(),
                            customer_tier="vip", policy_snippets=[{}]))
    assert out["target_team"] in {"senior_agent", "replacement_team"}


def test_route_repeated_contact():
    out = check_risk(_state(intent="return_request", sentiment="neutral", confidence=0.9,
                            order_context=angry_repeated_contact(), policy_snippets=[{}]))
    assert out["risk_band"] in {"approval_required", "escalate"}
    assert out["target_team"]


def test_route_low_confidence_with_no_context():
    # low_confidence is severity 40 — below MIN_FLAG_ROUTE_SEVERITY (50), so it
    # no longer auto-flags. It remains in matched_routes for explainability,
    # but the band stays auto unless the weighted score crosses FLAG_THRESHOLD
    # or a higher-severity route also matches. The graph's clarify node already
    # handles very-low-confidence messages separately.
    out = check_risk(_state(intent="general_faq", confidence=0.2, order_context=empty_context()))
    matched = [r["code"] for r in out.get("matched_routes") or []]
    assert "low_confidence" in matched
    assert out["risk_band"] == "auto"
    assert out["target_team"] == ""


def test_route_policy_exception_for_missing_policy():
    # policy_exception is severity 30 — below MIN_FLAG_ROUTE_SEVERITY (50), so
    # it no longer auto-flags. A KB coverage gap alone is not a customer-risk
    # signal; it still appears in matched_routes for explainability so the
    # auditor can see why the agent answered without policy backing.
    out = check_risk(_state(intent="warranty", confidence=0.9, order_context=regular_in_transit(),
                            policy_snippets=[]))
    matched = [r["code"] for r in out.get("matched_routes") or []]
    assert "policy_exception" in matched
    assert out["risk_band"] == "auto"
    assert out["target_team"] == ""


# ---------------------------------------------------------------------------
# Band assignment (auto / approval_required / escalate)
# ---------------------------------------------------------------------------
def test_band_auto_for_routine_query():
    out = check_risk(_state(intent="order_tracking", sentiment="neutral", confidence=0.95,
                            order_context=regular_in_transit()))
    assert out["risk_band"] == "auto"
    assert out["escalation_required"] is False
    assert out["requires_human_approval"] is False
    assert out["target_team"] == ""
    assert out["priority"] == "P4"


def test_band_approval_required_for_moderate_signal():
    out = check_risk(_state(intent="delivery_complaint", sentiment="negative", confidence=0.85,
                            order_context=lost_high_value_shipment()))
    # lost_shipment severity (70) is below FORCE_ESCALATE_SEVERITY (80) so
    # we expect approval_required on a sub-threshold score.
    assert out["risk_band"] in {"approval_required", "escalate"}
    assert out["requires_human_approval"] or out["escalation_required"]


def test_band_escalate_for_p1_route_regardless_of_score():
    # fraud route has severity 100 → always escalates, even with a benign score.
    out = check_risk(_state(intent="refund_status", sentiment="neutral", confidence=0.95,
                            order_context=fraud_signal_duplicate_refund()))
    assert out["risk_band"] == "escalate"
    assert out["escalation_required"] is True
    assert out["requires_human_approval"] is False


# ---------------------------------------------------------------------------
# Negative / false-positive guards (the original stub was prone to these)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("intent,sentiment,ctx_factory", [
    ("order_tracking", "neutral", regular_in_transit),
    ("product_inquiry", "positive", delivered_no_issue),
    ("coupon_issue", "neutral", regular_in_transit),
    ("general_faq", "positive", delivered_no_issue),
])
def test_routine_cases_do_not_escalate(intent, sentiment, ctx_factory):
    out = check_risk(_state(intent=intent, sentiment=sentiment, confidence=0.9,
                            order_context=ctx_factory()))
    assert out["escalation_required"] is False, (
        f"{intent}/{sentiment} should not escalate but produced reason={out['escalation_reason']}"
    )


def test_low_value_damaged_does_not_trigger_replacement_team():
    out = check_risk(_state(intent="damaged_product", sentiment="negative", confidence=0.9,
                            order_context=damaged_low_value(), policy_snippets=[{}]))
    assert out["target_team"] != "replacement_team"


# ---------------------------------------------------------------------------
# Output contract (schema-shape tests)
# ---------------------------------------------------------------------------
REQUIRED_KEYS = {
    "risk_score", "risk_band", "risk_factors", "matched_routes",
    "escalation_required", "escalation_reason", "target_team",
    "priority", "sla_target", "requires_human_approval",
    "agents_called", "audit_trail",
}


def test_output_contains_all_required_keys():
    out = check_risk(_state(intent="return_request", order_context=regular_in_transit(),
                            policy_snippets=[{}]))
    assert REQUIRED_KEYS.issubset(set(out.keys()))


def test_audit_trail_present():
    out = check_risk(_state(intent="order_tracking", order_context=regular_in_transit()))
    assert "escalation_risk" in out["agents_called"]
    assert len(out["audit_trail"]) >= 1
    assert out["audit_trail"][0]["agent"] == "escalation_risk"


def test_risk_factors_are_explainable():
    out = check_risk(_state(intent="damaged_product", sentiment="angry", confidence=0.9,
                            order_context=damaged_vip_high_value(), customer_tier="vip",
                            policy_snippets=[{}]))
    factors = out["risk_factors"]
    assert {f["name"] for f in factors} == set(WEIGHTS.keys())
    for f in factors:
        assert 0.0 <= f["raw"] <= 1.0
        assert 0.0 <= f["contribution"] <= f["weight"]
        assert f["detail"]


def test_sla_target_is_iso_when_escalating():
    out = check_risk(_state(intent="refund_status", order_context=fraud_signal_duplicate_refund()))
    assert out["sla_target"]  # ISO timestamp string
    # ISO8601 strings are easy to round-trip via fromisoformat
    from datetime import datetime
    datetime.fromisoformat(out["sla_target"])


# ---------------------------------------------------------------------------
# Resilience tests
# ---------------------------------------------------------------------------
def test_handles_missing_state_fields():
    out = check_risk({})
    assert out["risk_band"] in {"auto", "approval_required", "escalate"}
    assert "risk_score" in out
    assert isinstance(out["risk_factors"], list)


def test_handles_garbage_sentiment():
    out = check_risk(_state(sentiment="completely_made_up_emotion"))
    assert 0.0 <= out["risk_score"] <= 1.0


def test_handles_string_amount():
    state = _state(order_context={"payment": {"amount": "not-a-number"}})
    out = check_risk(state)
    assert out["risk_score"] >= 0.0


# ---------------------------------------------------------------------------
# Governance integration tests (audit + approval queue)
# ---------------------------------------------------------------------------
def test_audit_entry_round_trips(tmp_path: Path):
    from src.governance.audit import (
        AuditEntry,
        build_audit_entry_from_state,
        load_audit_logs,
        save_audit_log,
    )
    state_after_risk = check_risk(_state(intent="damaged_product", sentiment="angry",
                                         order_context=damaged_vip_high_value(),
                                         customer_tier="vip", policy_snippets=[{}]))
    merged = {**_state(intent="damaged_product"), **state_after_risk, "session_id": "S-001",
              "customer_id": "CUST_TEST", "channel": "web"}
    entry = build_audit_entry_from_state(merged, resolution_time_ms=12.5)
    path = tmp_path / "audit.jsonl"
    save_audit_log(entry, path)
    save_audit_log(entry, path)

    loaded = load_audit_logs(path)
    assert len(loaded) == 2
    assert all(isinstance(e, AuditEntry) for e in loaded)
    assert loaded[0].session_id == "S-001"
    assert loaded[0].escalation == state_after_risk["escalation_required"]
    assert loaded[0].risk_band == state_after_risk["risk_band"]


def test_audit_report_aggregates(tmp_path: Path):
    from src.governance.audit import (
        build_audit_entry_from_state,
        generate_audit_report,
        save_audit_log,
    )
    path = tmp_path / "audit.jsonl"

    scenarios = [
        _state(intent="order_tracking", order_context=regular_in_transit()),
        _state(intent="damaged_product", sentiment="angry",
               order_context=damaged_vip_high_value(), customer_tier="vip", policy_snippets=[{}]),
        _state(intent="refund_status", order_context=fraud_signal_duplicate_refund()),
    ]
    for i, s in enumerate(scenarios):
        merged = {**s, **check_risk(s), "session_id": f"S-{i}", "customer_id": f"C-{i}", "channel": "web"}
        save_audit_log(build_audit_entry_from_state(merged), path)

    report = generate_audit_report(load_logs := __import__("src.governance.audit", fromlist=["load_audit_logs"]).load_audit_logs(path))
    assert report["total_sessions"] == 3
    assert 0.0 <= report["escalation_rate"] <= 1.0
    assert report["intent_distribution"]


def test_approval_queue_submit_and_decide(tmp_path: Path):
    from src.governance import approval_queue

    queue_path = tmp_path / "approvals.jsonl"
    rec = approval_queue.submit_for_approval(
        session_id="S-1", customer_id="CUST_1", intent="return_request",
        risk_score=0.45, target_team="senior_agent", priority="P3",
        sla_target="2026-05-22T00:00:00+00:00",
        draft_response="Here is your draft response.",
        references_cited=["POL-RET-ELEC-001"],
        risk_factors=[],
        filepath=queue_path,
    )
    assert rec.status == "pending"
    assert rec.approval_id.startswith("APR-")
    pending = approval_queue.list_pending(queue_path)
    assert len(pending) == 1

    decided = approval_queue.approve(rec.approval_id, reviewer="qa-bot",
                                     note="LGTM", filepath=queue_path)
    assert decided is not None
    assert decided.status == "approved"
    assert decided.reviewer == "qa-bot"

    # Second approve is a no-op (idempotent).
    again = approval_queue.approve(rec.approval_id, reviewer="qa-bot", filepath=queue_path)
    assert again is not None and again.status == "approved"

    assert approval_queue.list_pending(queue_path) == []


def test_approval_queue_auto_approve_env(monkeypatch, tmp_path: Path):
    from src.governance import approval_queue

    monkeypatch.setenv("APPROVAL_AUTO_APPROVE", "true")
    rec = approval_queue.submit_for_approval(
        session_id="S-2", customer_id="CUST_2", intent="warranty",
        risk_score=0.5, target_team="manager", priority="P3", sla_target="",
        draft_response="Draft.", filepath=tmp_path / "approvals.jsonl",
    )
    assert rec.status == "auto_approved"
    assert rec.reviewer == "auto"


def test_approval_queue_cli_smoke(tmp_path: Path, capsys):
    from src.governance import approval_queue

    queue_path = tmp_path / "approvals.jsonl"
    approval_queue.submit_for_approval(
        session_id="S-CLI", customer_id="CUST_CLI", intent="coupon_issue",
        risk_score=0.42, target_team="manager", priority="P3", sla_target="",
        draft_response="Draft.", filepath=queue_path,
    )
    exit_code = approval_queue.main(["--file", str(queue_path), "list", "--status", "pending"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "APR-" in captured.out
    assert "pending" in captured.out
