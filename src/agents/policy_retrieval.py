"""
Policy Retrieval Agent (Person 2)

Searches approved return, refund, warranty, delivery, seller, and coupon
policies. Returns matched policy snippets with references and confidence.

TODO(Person 2): Replace keyword matching with vector/RAG retrieval using
the knowledge base files in src/knowledge/policies/. Build a proper
retrieval pipeline with embeddings and similarity search.
"""

from __future__ import annotations
from datetime import datetime, timezone

from src.orchestrator.state import AgentState


# Mock policy knowledge base — Person 2 will replace with RAG retrieval
MOCK_POLICIES = {
    "return_request": [
        {
            "rule": "Electronics can be returned within 7 days of delivery if unopened and in original packaging.",
            "explanation": "Standard return window for electronics category.",
            "reference_id": "POL-RET-ELEC-001",
            "confidence": 0.92,
        },
        {
            "rule": "Fashion items can be returned within 15 days of delivery. Items must be unworn with tags attached.",
            "explanation": "Extended return window for fashion category.",
            "reference_id": "POL-RET-FASH-001",
            "confidence": 0.90,
        },
    ],
    "refund_status": [
        {
            "rule": "Refunds are processed within 5-7 business days after return pickup is completed.",
            "explanation": "Standard refund processing timeline.",
            "reference_id": "POL-REF-TIME-001",
            "confidence": 0.95,
        },
        {
            "rule": "UPI and wallet refunds are credited within 24 hours. Card refunds take 5-7 business days.",
            "explanation": "Refund timelines vary by payment method.",
            "reference_id": "POL-REF-METHOD-001",
            "confidence": 0.93,
        },
    ],
    "warranty": [
        {
            "rule": "Electronics carry 1-year manufacturer warranty from date of delivery. Physical damage is not covered.",
            "explanation": "Standard warranty coverage for electronics.",
            "reference_id": "POL-WAR-ELEC-001",
            "confidence": 0.91,
        },
    ],
    "coupon_issue": [
        {
            "rule": "Coupons are valid only on items marked 'coupon eligible'. Minimum cart value and category restrictions apply.",
            "explanation": "Coupon applicability rules.",
            "reference_id": "POL-CPN-ELIG-001",
            "confidence": 0.89,
        },
        {
            "rule": "Only one coupon can be applied per order. Coupons cannot be combined with flash sale prices.",
            "explanation": "Coupon stacking restriction.",
            "reference_id": "POL-CPN-STACK-001",
            "confidence": 0.94,
        },
    ],
    "delivery_complaint": [
        {
            "rule": "If delivery is delayed beyond estimated date by more than 3 days, customer is eligible for shipping fee refund.",
            "explanation": "Delayed delivery compensation policy.",
            "reference_id": "POL-DEL-DELAY-001",
            "confidence": 0.88,
        },
    ],
    "damaged_product": [
        {
            "rule": "Damaged or defective products must be reported within 48 hours of delivery with photo evidence. Replacement or full refund will be provided.",
            "explanation": "Damaged product reporting and resolution policy.",
            "reference_id": "POL-DMG-REPORT-001",
            "confidence": 0.96,
        },
    ],
}


def retrieve_policy(state: AgentState) -> AgentState:
    """
    LangGraph node: retrieves relevant policy snippets for the detected intent.

    Reads: intent, message, order_context
    Writes: policy_snippets, policy_applies, agents_called, audit_trail

    TODO(Person 2): Replace with:
      1. Embed the customer query
      2. Search vector store of policy documents
      3. Return top-k matched policies with confidence scores
      4. Include reference IDs for audit trail
    """
    intent = state.get("intent", "")

    snippets = MOCK_POLICIES.get(intent, [])
    policy_applies = len(snippets) > 0

    return {
        "policy_snippets": snippets,
        "policy_applies": policy_applies,
        "agents_called": ["policy_retrieval"],
        "audit_trail": [{
            "agent": "policy_retrieval",
            "action": "retrieve_policy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"intent={intent}, policies_found={len(snippets)}, applies={policy_applies}",
        }],
    }
