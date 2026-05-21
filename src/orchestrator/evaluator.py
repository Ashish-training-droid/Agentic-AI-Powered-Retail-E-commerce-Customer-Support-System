"""
Quality Evaluator / Gate (Ashish (Person 1))

Runs after context agents and before response generation. Checks:
- Are all required context fields populated?
- Is intent confidence above threshold?
- Does policy apply and was it retrieved?
- Were there any agent errors in the pipeline?
- Computes an overall quality score and suggests fallback strategy.
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

    Reads: intent, intent_confidence, order_context, policy_snippets, product_context, audit_trail
    Writes: quality_score, quality_issues, agents_called, audit_trail

    Detects:
    - Low confidence classifications
    - Missing order data for order-dependent intents
    - Missing policy data for policy-dependent intents
    - Agent errors that occurred during the pipeline
    - Empty product context for product inquiries
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
            issues.append("Order context missing — customer did not provide order ID or order not found in system")

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
            issues.append("No policy retrieved for policy-dependent intent — response may lack grounding")

    # Check 4: Product context for product inquiries
    if intent == "product_inquiry":
        product_ctx = state.get("product_context", {})
        if product_ctx and product_ctx.get("comparison"):
            scores.append(1.0)
        else:
            scores.append(0.5)
            issues.append("No product data found — may not have matched any catalog items")

    # Check 5: Agent errors in audit trail
    audit_trail = state.get("audit_trail", [])
    error_agents = [
        entry.get("agent", "unknown")
        for entry in audit_trail
        if "ERROR" in entry.get("action", "")
    ]
    if error_agents:
        scores.append(0.2)
        issues.append(f"Agent errors detected: {', '.join(error_agents)} — response may be incomplete")

    # Check 6: Workflow action failed
    action_result = state.get("action_result", {})
    if action_result and action_result.get("success") is False:
        scores.append(0.5)
        issues.append(f"Workflow action failed: {action_result.get('message', 'unknown error')}")

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
            "details": f"score={quality_score:.2f}, issues={len(issues)}: {'; '.join(issues) if issues else 'none'}",
        }],
    }
