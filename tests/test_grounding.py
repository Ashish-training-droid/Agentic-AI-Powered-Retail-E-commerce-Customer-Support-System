"""
Grounding tests for the Policy Retrieval Agent (Person 2).

Verifies that:
- The correct policy is returned for common customer intents
- Reference IDs follow the POL-XXX-YYY-NNN format
- Edge cases return either a valid match or no match (not garbage)
"""

from __future__ import annotations

import re
import pytest

from src.agents.policy_retrieval import retrieve_policy


REF_ID_PATTERN = re.compile(r"^POL-[A-Z]+-[A-Z]+-\d+$")


def _run(intent: str, message: str) -> dict:
    """Helper to invoke the agent with a minimal state."""
    state = {"intent": intent, "message": message}
    return retrieve_policy(state)


# --------------------------------------------------------------------------
# 10 happy-path tests — correct policy retrieved for typical intents
# --------------------------------------------------------------------------

@pytest.mark.parametrize("intent,message,expected_prefix", [
    ("return_request",     "I want to return my laptop, it's been 3 days",   "POL-RET"),
    ("return_request",     "Can I return this shirt? Tags are still on",     "POL-RET"),
    ("refund_status",      "When will I get my refund? Paid by UPI",         "POL-REF"),
    ("refund_status",      "My card refund hasn't come yet",                 "POL-REF"),
    ("warranty",           "How do I claim warranty on my phone?",           "POL-WAR"),
    ("coupon_issue",       "My coupon FESTIVE10 is not working",             "POL-CPN"),
    ("coupon_issue",       "Can I use two coupons together?",                "POL-CPN"),
    ("delivery_complaint", "My order is delayed by 5 days",                  "POL-DEL"),
    ("damaged_product",    "Received a broken headphone, what do I do?",     "POL-"),
    ("order_tracking",     "Where is my order? Address change possible?",    "POL-DEL"),
])
def test_correct_policy_retrieved(intent, message, expected_prefix):
    result = _run(intent, message)
    assert result["policy_applies"] is True, f"No policy for intent={intent}"
    assert len(result["policy_snippets"]) > 0
    top_ref = result["policy_snippets"][0]["reference_id"]
    assert top_ref.startswith(expected_prefix), (
        f"Expected ref starting with {expected_prefix}, got {top_ref}"
    )


# --------------------------------------------------------------------------
# Reference-ID format check
# --------------------------------------------------------------------------

def test_reference_ids_follow_format():
    result = _run("return_request", "I want to return my electronics item")
    for snippet in result["policy_snippets"]:
        assert REF_ID_PATTERN.match(snippet["reference_id"]), (
            f"Bad reference id: {snippet['reference_id']}"
        )


# --------------------------------------------------------------------------
# Confidence sanity
# --------------------------------------------------------------------------

def test_confidence_in_valid_range():
    result = _run("refund_status", "Where is my refund?")
    for snippet in result["policy_snippets"]:
        assert 0.0 <= snippet["confidence"] <= 1.0


# --------------------------------------------------------------------------
# Audit trail must always be appended
# --------------------------------------------------------------------------

def test_audit_trail_present():
    result = _run("return_request", "Return please")
    assert "agents_called" in result
    assert "policy_retrieval" in result["agents_called"]
    assert len(result["audit_trail"]) >= 1
    assert result["audit_trail"][0]["agent"] == "policy_retrieval"


# --------------------------------------------------------------------------
# 5 edge cases
# --------------------------------------------------------------------------

def test_unknown_intent_returns_no_policy():
    result = _run("totally_unknown_intent", "random message")
    assert result["policy_applies"] is False
    assert result["policy_snippets"] == []


def test_empty_message_with_known_intent_still_works():
    result = _run("return_request", "")
    # Should still match return policies via intent category alone
    assert result["policy_applies"] is True


def test_product_inquiry_intent_no_policy_needed():
    # Product inquiries don't need policy grounding
    result = _run("product_inquiry", "Compare iPhone and Samsung")
    assert result["policy_applies"] is False


def test_ambiguous_message_returns_best_guess():
    result = _run("general_faq", "How do I cancel my order?")
    assert result["policy_applies"] is True
    refs = [s["reference_id"] for s in result["policy_snippets"]]
    assert any("CANCEL" in r or "GEN" in r for r in refs)


def test_top_snippets_capped_at_three():
    result = _run("return_request", "return refund warranty coupon delivery")
    assert len(result["policy_snippets"]) <= 3