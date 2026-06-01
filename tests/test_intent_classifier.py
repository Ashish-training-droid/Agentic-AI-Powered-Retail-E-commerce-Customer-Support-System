"""
Unit Tests for Intent Classifier

Tests the classification accuracy for all 9 supported intents using
mock mode (keyword-based). These serve as baseline tests that Rohan (Person 5)
will expand with the full evaluation suite.

Run: python -m pytest tests/test_intent_classifier.py -v
  OR: python tests/test_intent_classifier.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["USE_MOCK"] = "true"

from src.agents.intent_classifier import classify_intent


def _classify(message: str, channel: str = "web") -> dict:
    """Helper to classify a message and return the state update."""
    state = {"message": message, "channel": channel, "conversation_history": []}
    return classify_intent(state)


def test_order_tracking():
    result = _classify("Where is my order SE10234?")
    assert result["intent"] == "order_tracking"
    assert result["intent_confidence"] >= 0.7
    print("PASS: order_tracking")


def test_return_request():
    result = _classify("I want to return this product")
    assert result["intent"] == "return_request"
    assert result["intent_confidence"] >= 0.7
    print("PASS: return_request")


def test_refund_status():
    result = _classify("When will I get my refund?")
    assert result["intent"] == "refund_status"
    assert result["intent_confidence"] >= 0.7
    print("PASS: refund_status")


def test_product_inquiry():
    result = _classify("Compare the HP Pavilion and Lenovo IdeaPad laptops")
    assert result["intent"] == "product_inquiry"
    assert result["intent_confidence"] >= 0.7
    print("PASS: product_inquiry")


def test_warranty():
    result = _classify("Is my warranty still valid?")
    assert result["intent"] == "warranty"
    assert result["intent_confidence"] >= 0.7
    print("PASS: warranty")


def test_coupon_issue():
    result = _classify("My coupon SAVE20 was not applied to my cart")
    assert result["intent"] == "coupon_issue"
    assert result["intent_confidence"] >= 0.7
    print("PASS: coupon_issue")


def test_delivery_complaint():
    result = _classify("My package is lost and never arrived")
    assert result["intent"] == "delivery_complaint"
    assert result["intent_confidence"] >= 0.7
    print("PASS: delivery_complaint")


def test_damaged_product():
    result = _classify("I received a damaged item, the box was broken")
    assert result["intent"] == "damaged_product"
    assert result["intent_confidence"] >= 0.7
    print("PASS: damaged_product")


def test_general_faq_fallback():
    result = _classify("What are your store hours?")
    assert result["intent"] == "general_faq"
    print("PASS: general_faq")


def test_empty_message_low_confidence():
    result = _classify("hi")
    assert result["intent_confidence"] <= 0.4
    print("PASS: empty message gives low confidence")


def test_sentiment_detection_angry():
    result = _classify("This is broken and I am furious about the damage!")
    assert result["sentiment"] == "angry"
    print("PASS: angry sentiment detected")


def test_always_returns_required_fields():
    result = _classify("random text here")
    assert "intent" in result
    assert "sentiment" in result
    assert "urgency" in result
    assert "intent_confidence" in result
    assert "agents_called" in result
    assert "audit_trail" in result
    print("PASS: all required fields present")


if __name__ == "__main__":
    tests = [
        test_order_tracking,
        test_return_request,
        test_refund_status,
        test_product_inquiry,
        test_warranty,
        test_coupon_issue,
        test_delivery_complaint,
        test_damaged_product,
        test_general_faq_fallback,
        test_empty_message_low_confidence,
        test_sentiment_detection_angry,
        test_always_returns_required_fields,
    ]

    print("=" * 60)
    print("  Intent Classifier Unit Tests")
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
