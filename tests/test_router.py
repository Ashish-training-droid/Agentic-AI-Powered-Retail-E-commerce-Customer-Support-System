"""
Unit Tests for Router Logic

Tests that the router correctly decides which agents to call
based on intent, confidence, and data availability.

Run: python -m pytest tests/test_router.py -v
  OR: python tests/test_router.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.orchestrator.router import (
    determine_route,
    route_after_intent,
    route_after_order,
    route_after_policy,
    route_after_risk,
)


def test_order_tracking_routes_to_order_context():
    state = {"intent": "order_tracking", "intent_confidence": 0.9, "message": "Where is SE10234", "customer_id": "CUST_1001"}
    agents = determine_route(state)
    assert "order_context" in agents
    assert route_after_intent(state) == "fetch_order"
    print("PASS: order_tracking routes to fetch_order")


def test_return_request_routes_to_all_three():
    state = {"intent": "return_request", "intent_confidence": 0.9, "message": "return SE10567", "customer_id": "CUST_1002"}
    agents = determine_route(state)
    assert "order_context" in agents
    assert "policy_retrieval" in agents
    assert "workflow_automation" in agents
    print("PASS: return_request routes to order + policy + workflow")


def test_product_inquiry_routes_to_advisory():
    state = {"intent": "product_inquiry", "intent_confidence": 0.9, "message": "compare laptops", "customer_id": "CUST_1001"}
    assert route_after_intent(state) == "advise_product"
    print("PASS: product_inquiry routes to advise_product")


def test_coupon_issue_routes_to_policy_only():
    state = {"intent": "coupon_issue", "intent_confidence": 0.9, "message": "coupon not working", "customer_id": "CUST_1001"}
    assert route_after_intent(state) == "retrieve_policy"
    print("PASS: coupon_issue routes to retrieve_policy")


def test_general_faq_routes_to_direct_response():
    state = {"intent": "general_faq", "intent_confidence": 0.8, "message": "What are store hours", "customer_id": "CUST_1001"}
    assert route_after_intent(state) == "direct_response"
    print("PASS: general_faq routes to direct_response")


def test_low_confidence_routes_to_clarify():
    state = {"intent": "general_faq", "intent_confidence": 0.2, "message": "hi", "customer_id": "CUST_1001"}
    assert route_after_intent(state) == "clarify"
    print("PASS: low confidence routes to clarify")


def test_moderate_confidence_proceeds():
    state = {"intent": "order_tracking", "intent_confidence": 0.5, "message": "order status SE10234", "customer_id": "CUST_1001"}
    result = route_after_intent(state)
    assert result != "clarify"
    print("PASS: moderate confidence (0.5) still proceeds")


def test_order_not_found_skips_policy():
    state = {"intent": "order_tracking", "order_context": {}, "intent_confidence": 0.9, "message": "where is my order"}
    result = route_after_order(state)
    assert result == "evaluate"
    print("PASS: empty order context skips to evaluate")


def test_order_found_proceeds_to_policy():
    state = {"intent": "return_request", "order_context": {"order_id": "SE10234"}, "intent_confidence": 0.9, "message": "return SE10234"}
    result = route_after_order(state)
    assert result == "retrieve_policy"
    print("PASS: order found proceeds to policy retrieval")


def test_policy_with_workflow_proceeds():
    state = {"intent": "return_request", "policy_snippets": [{"rule": "test"}], "intent_confidence": 0.9, "message": "return"}
    result = route_after_policy(state)
    assert result == "execute_workflow"
    print("PASS: policy found proceeds to workflow")


def test_policy_without_workflow_skips():
    state = {"intent": "refund_status", "policy_snippets": [{"rule": "test"}], "intent_confidence": 0.9, "message": "refund"}
    result = route_after_policy(state)
    assert result == "evaluate"
    print("PASS: refund_status skips workflow after policy")


def test_risk_escalation_routes_correctly():
    state_safe = {"escalation_required": False}
    state_escalate = {"escalation_required": True}
    assert route_after_risk(state_safe) == "generate_response"
    assert route_after_risk(state_escalate) == "escalate"
    print("PASS: risk routing works for both paths")


def test_no_customer_id_no_order_id_strict_intent():
    state = {"intent": "order_tracking", "intent_confidence": 0.9, "message": "where is my order", "customer_id": ""}
    result = route_after_intent(state)
    assert result == "direct_response"
    print("PASS: strict intent with no IDs goes to direct_response")


if __name__ == "__main__":
    tests = [
        test_order_tracking_routes_to_order_context,
        test_return_request_routes_to_all_three,
        test_product_inquiry_routes_to_advisory,
        test_coupon_issue_routes_to_policy_only,
        test_general_faq_routes_to_direct_response,
        test_low_confidence_routes_to_clarify,
        test_moderate_confidence_proceeds,
        test_order_not_found_skips_policy,
        test_order_found_proceeds_to_policy,
        test_policy_with_workflow_proceeds,
        test_policy_without_workflow_skips,
        test_risk_escalation_routes_correctly,
        test_no_customer_id_no_order_id_strict_intent,
    ]

    print("=" * 60)
    print("  Router Logic Unit Tests")
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
