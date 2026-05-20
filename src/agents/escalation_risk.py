"""
Escalation & Risk Agent (Person 5)

Detects high-risk, low-confidence, angry, fraud, or compliance-sensitive
cases and routes them to the correct human team.

TODO(Person 5): Replace basic rules with a comprehensive risk matrix.
Add fraud detection signals, repeated contact detection, and dynamic
priority scoring based on customer tier and order value.
"""

from __future__ import annotations
from datetime import datetime, timezone

from src.orchestrator.state import AgentState
from src.config import CONFIDENCE_THRESHOLD_LOW


# Risk routing rules — Person 5 will expand into full risk matrix
ESCALATION_ROUTES = {
    "fraud": {"team": "fraud_review", "priority": "P1"},
    "payment_dispute": {"team": "refund_specialist", "priority": "P2"},
    "damaged_high_value": {"team": "replacement_team", "priority": "P2"},
    "lost_shipment": {"team": "logistics", "priority": "P2"},
    "angry_high_value": {"team": "senior_agent", "priority": "P1"},
    "low_confidence": {"team": "senior_agent", "priority": "P3"},
    "repeated_contact": {"team": "escalation_queue", "priority": "P3"},
}


def check_risk(state: AgentState) -> AgentState:
    """
    LangGraph node: evaluates risk and determines if escalation is needed.

    Reads: intent, sentiment, urgency, intent_confidence, order_context, action_result
    Writes: risk_score, escalation_required, escalation_reason, target_team, priority, agents_called, audit_trail

    TODO(Person 5): Implement:
      1. Multi-factor risk scoring (sentiment + value + history + confidence)
      2. Fraud signal detection (duplicate refunds, suspicious patterns)
      3. Repeated contact detection from CRM history
      4. Dynamic priority calculation
      5. Routing map with team availability awareness
    """
    sentiment = state.get("sentiment", "neutral")
    intent = state.get("intent", "")
    confidence = state.get("intent_confidence", 1.0)
    order_context = state.get("order_context", {})
    order_value = order_context.get("payment", {}).get("amount", 0)

    risk_score = 0.0
    escalation_required = False
    escalation_reason = ""
    target_team = ""
    priority = "P4"

    # Rule 1: Angry sentiment with high-value order
    if sentiment == "angry" and order_value > 5000:
        risk_score = max(risk_score, 0.8)
        escalation_required = True
        escalation_reason = "Angry customer with high-value order"
        route = ESCALATION_ROUTES["angry_high_value"]
        target_team = route["team"]
        priority = route["priority"]

    # Rule 2: Damaged high-value product
    if intent == "damaged_product" and order_value > 10000:
        risk_score = max(risk_score, 0.85)
        escalation_required = True
        escalation_reason = "Damaged high-value product requires specialist review"
        route = ESCALATION_ROUTES["damaged_high_value"]
        target_team = route["team"]
        priority = route["priority"]

    # Rule 3: Low confidence — system unsure
    if confidence < CONFIDENCE_THRESHOLD_LOW:
        risk_score = max(risk_score, 0.6)
        escalation_required = True
        escalation_reason = "Low classification confidence — needs human review"
        route = ESCALATION_ROUTES["low_confidence"]
        target_team = route["team"]
        priority = route["priority"]

    # Rule 4: Lost shipment
    shipment_status = order_context.get("shipment", {}).get("status", "")
    if intent == "delivery_complaint" and shipment_status == "lost":
        risk_score = max(risk_score, 0.75)
        escalation_required = True
        escalation_reason = "Shipment marked as lost"
        route = ESCALATION_ROUTES["lost_shipment"]
        target_team = route["team"]
        priority = route["priority"]

    # Default risk for non-escalated cases
    if not escalation_required:
        if sentiment == "negative":
            risk_score = 0.3
        elif sentiment == "angry":
            risk_score = 0.5
        else:
            risk_score = 0.1
        priority = "P4"

    return {
        "risk_score": risk_score,
        "escalation_required": escalation_required,
        "escalation_reason": escalation_reason,
        "target_team": target_team,
        "priority": priority,
        "agents_called": ["escalation_risk"],
        "audit_trail": [{
            "agent": "escalation_risk",
            "action": "evaluate_risk",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"risk={risk_score:.2f}, escalate={escalation_required}, team={target_team}",
        }],
    }
