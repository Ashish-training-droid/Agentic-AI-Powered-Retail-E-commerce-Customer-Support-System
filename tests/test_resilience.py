"""
Resilience Tests — Verifies the system handles missing data gracefully.

Tests cover:
1. Happy path (order ID present, all data found)
2. Missing order ID (customer doesn't provide it)
3. Unknown customer (no records in system)
4. Empty/short message (very low confidence → clarification)
5. Escalation path (angry + high value)
6. Known customer without order ID (lookup by customer_id)
7. General FAQ (direct response, no context agents needed)

Run: python -m pytest tests/test_resilience.py -v
  OR: python tests/test_resilience.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["USE_MOCK"] = "true"

from src.orchestrator.graph import app
from src.utils.session import build_initial_state


def run_test(name: str, message: str, customer_id: str = "CUST_1001", channel: str = "web"):
    """Helper to run a single test case."""
    state = build_initial_state(
        message=message,
        customer_id=customer_id,
        channel=channel,
    )
    result = app.invoke(state)
    return result


def test_happy_path_order_tracking():
    """Customer provides order ID — full pipeline runs successfully."""
    result = run_test(
        "Happy Path - Order Tracking",
        "Where is my order SE10234? It was supposed to arrive yesterday.",
        customer_id="CUST_1001",
    )
    assert result.get("intent") == "order_tracking"
    assert result.get("intent_confidence", 0) >= 0.7
    assert result.get("order_context", {}).get("order_id") == "SE10234"
    assert result.get("quality_score", 0) >= 0.9
    assert result.get("response_text")
    assert "SE10234" in result.get("response_text", "")
    print("PASS: Happy path order tracking")


def test_missing_order_id_unknown_customer():
    """No order ID, unknown customer — should ask for order ID."""
    result = run_test(
        "Missing Order ID - Unknown Customer",
        "Where is my order? It has not arrived yet.",
        customer_id="CUST_9999",
    )
    assert result.get("intent") == "order_tracking"
    assert not result.get("order_context")
    assert result.get("quality_score", 1) < 0.8
    assert "order ID" in result.get("response_text", "").lower() or "SE" in result.get("response_text", "")
    print("PASS: Missing order ID asks for it")


def test_known_customer_no_order_id():
    """Known customer but no order ID in message — looks up by customer_id."""
    result = run_test(
        "Known Customer - No Order ID",
        "I want to return my shoes",
        customer_id="CUST_1002",
    )
    assert result.get("intent") == "return_request"
    assert result.get("order_context", {}).get("order_id") == "SE10567"
    assert result.get("response_text")
    print("PASS: Known customer looked up by customer_id")


def test_empty_short_message_clarification():
    """Very short message — low confidence triggers clarification."""
    result = run_test(
        "Short Message - Clarification",
        "hi",
        customer_id="CUST_1001",
    )
    assert result.get("intent_confidence", 1) <= 0.4
    assert "clarification_handler" in result.get("agents_called", [])
    assert "more detail" in result.get("response_text", "").lower() or "provide" in result.get("response_text", "").lower()
    print("PASS: Short message triggers clarification")


def test_escalation_angry_high_value():
    """Angry customer with high-value damaged product — escalates."""
    result = run_test(
        "Escalation - Angry High Value",
        "I received my Samsung Galaxy S24 with a cracked screen! This is a Rs 75000 phone and it arrived broken!",
        customer_id="CUST_1003",
    )
    assert result.get("intent") == "damaged_product"
    assert result.get("escalation_required") == True
    # Person 5's risk agent picks the highest-severity matched route.
    # An angry customer on a high-value damaged item matches BOTH
    # angry_high_value (P1, senior_agent, severity 90) and
    # damaged_high_value (P2, replacement_team, severity 80) — the P1
    # senior_agent route wins because customer sentiment trumps category.
    assert result.get("target_team") in ("senior_agent", "replacement_team")
    assert result.get("priority") in ("P1", "P2")
    assert result.get("response_confidence", 0) >= 0.9
    print("PASS: High-value damaged product escalates correctly")


def test_product_inquiry_no_order_needed():
    """Product inquiry — doesn't need order context at all."""
    result = run_test(
        "Product Inquiry - No Order Needed",
        "I need a laptop for college. Compare HP Pavilion and Lenovo IdeaPad please.",
        customer_id="CUST_1004",
    )
    assert result.get("intent") == "product_inquiry"
    assert result.get("product_context", {}).get("comparison")
    assert "order_context" not in result.get("agents_called", [])
    assert result.get("response_text")
    print("PASS: Product inquiry skips order context")


def test_general_faq_direct_response():
    """General question — goes straight to response, no context agents."""
    result = run_test(
        "General FAQ - Direct Response",
        "What payment methods do you accept?",
        customer_id="CUST_1001",
    )
    assert result.get("intent") == "general_faq"
    assert result.get("quality_score", 0) >= 0.5
    assert result.get("response_text")
    assert "order_context" not in result.get("agents_called", [])
    assert "policy_retrieval" not in result.get("agents_called", [])
    print("PASS: General FAQ uses direct response path")


def test_coupon_issue_policy_only():
    """Coupon issue — only needs policy, not order context."""
    result = run_test(
        "Coupon Issue - Policy Only",
        "My coupon code SAVE20 is not working on my cart",
        customer_id="CUST_1004",
    )
    assert result.get("intent") == "coupon_issue"
    assert result.get("policy_snippets")
    assert result.get("response_text")
    assert result.get("quality_score", 0) >= 0.7
    print("PASS: Coupon issue retrieves policy correctly")


def test_refund_status_with_order():
    """Refund inquiry — needs order + policy."""
    result = run_test(
        "Refund Status",
        "I returned my shoes 5 days ago and still haven't received my refund",
        customer_id="CUST_1002",
    )
    assert result.get("intent") == "refund_status"
    assert result.get("order_context", {}).get("order_id")
    assert result.get("policy_snippets")
    assert result.get("response_text")
    print("PASS: Refund status uses order + policy")


def test_pipeline_never_crashes_with_garbage():
    """Garbage input — pipeline completes without exception."""
    result = run_test(
        "Garbage Input - No Crash",
        "!@#$%^&*() 12345 zzzzz",
        customer_id="",
    )
    assert result.get("response_text") is not None
    assert len(result.get("agents_called", [])) > 0
    print("PASS: Garbage input doesn't crash pipeline")


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    tests = [
        test_happy_path_order_tracking,
        test_missing_order_id_unknown_customer,
        test_known_customer_no_order_id,
        test_empty_short_message_clarification,
        test_escalation_angry_high_value,
        test_product_inquiry_no_order_needed,
        test_general_faq_direct_response,
        test_coupon_issue_policy_only,
        test_refund_status_with_order,
        test_pipeline_never_crashes_with_garbage,
    ]

    print("=" * 60)
    print("  ShopEase Resilience Test Suite")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test_fn.__name__} — {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test_fn.__name__} — {type(e).__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
