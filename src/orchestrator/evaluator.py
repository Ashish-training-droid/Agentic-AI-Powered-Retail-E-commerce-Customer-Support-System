"""
Quality Evaluator / Gate (Person 1)

Runs after context agents and before response generation. Checks:
- Are all required context fields populated?
- Is intent confidence above threshold?
- Does policy apply and was it retrieved?
- Computes an overall quality score for the pipeline.

If quality is too low, flags the issue so the risk agent can escalate.
"""

from __future__ import annotations
from datetime import datetime, timezone

from src.config import (
    CONFIDENCE_THRESHOLD_PROCEED,
    CONFIDENCE_THRESHOLD_LOW,
    POLICY_MATCH_THRESHOLD,
)
from src.orchestrator.state import AgentState


# Intents that REQUIRE order context
ORDER_REQUIRED_INTENTS = {
    "order_tracking",
    "return_request",
    "refund_status",
    "delivery_complaint",
    "damaged_product",
}

# Intents that REQUIRE policy retrieval
POLICY_REQUIRED_INTENTS = {
    "return_request",
    "refund_status",
    "warranty",
    "coupon_issue",
    "damaged_product",
}


def evaluate_quality(state: AgentState) -> AgentState:
    """
    LangGraph node: evaluates the quality of gathered context before response.

    Reads: intent, intent_confidence, order_context, policy_snippets, product_context
    Writes: quality_score, quality_issues, agents_called, audit_trail
    """
    issues: list[str] = []
    scores: list[float] = []

    intent = state.get("intent", "")
    confidence = state.get("intent_confidence", 0.0)

    # Check 1: Intent confidence
    if confidence >= CONFIDENCE_THRESHOLD_PROCEED:
        scores.append(1.0)
    elif confidence >= CONFIDENCE_THRESHOLD_LOW:
        scores.append(0.6)
        issues.append(f"Intent confidence is moderate ({confidence:.2f}), response may need review")
    else:
        scores.append(0.2)
        issues.append(f"Intent confidence is LOW ({confidence:.2f}), recommend escalation")

    # Check 2: Order context populated when required
    if intent in ORDER_REQUIRED_INTENTS:
        order_ctx = state.get("order_context", {})
        if order_ctx and order_ctx.get("order_id"):
            scores.append(1.0)
        else:
            scores.append(0.3)
            issues.append("Order context missing for order-related intent")

    # Check 3: Policy retrieved when required
    if intent in POLICY_REQUIRED_INTENTS:
        policy_snippets = state.get("policy_snippets", [])
        if policy_snippets:
            max_policy_conf = max(p.get("confidence", 0) for p in policy_snippets)
            if max_policy_conf >= POLICY_MATCH_THRESHOLD:
                scores.append(1.0)
            else:
                scores.append(0.7)
                issues.append(f"Policy match confidence is moderate ({max_policy_conf:.2f})")
        else:
            scores.append(0.3)
            issues.append("No policy retrieved for policy-dependent intent")

    # Check 4: Product context for product inquiries
    if intent == "product_inquiry":
        product_ctx = state.get("product_context", {})
        if product_ctx and product_ctx.get("comparison"):
            scores.append(1.0)
        else:
            scores.append(0.5)
            issues.append("No product data found for product inquiry")

    # Compute overall quality score
    quality_score = sum(scores) / len(scores) if scores else 0.5

    return {
        "quality_score": quality_score,
        "quality_issues": issues,
        "agents_called": ["evaluator"],
        "audit_trail": [{
            "agent": "evaluator",
            "action": "quality_check",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"score={quality_score:.2f}, issues={len(issues)}",
        }],
    }
