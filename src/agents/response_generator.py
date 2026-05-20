"""
Response Generation Agent (Person 1 + Person 4)

Creates clear, brand-aligned, policy-grounded customer responses. Cites
policy references, adapts tone to channel, includes confidence score,
and flags ungrounded statements.

Uses OpenAI to generate natural language responses from structured context.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import OPENAI_API_KEY, OPENAI_MODEL, USE_MOCK
from src.orchestrator.state import AgentState


RESPONSE_SYSTEM_PROMPT = """You are the response generation agent for ShopEase customer support.

Your job is to create a clear, helpful, and brand-aligned response to the customer based on the context provided.

Rules:
1. ONLY state facts supported by the provided order context, policy snippets, or action results.
2. If a policy applies, cite the reference ID in brackets like [POL-RET-ELEC-001].
3. Adapt tone to the channel:
   - web/mobile chat: friendly, concise, use short paragraphs
   - email: professional, structured, include greeting/closing
   - social: brief, empathetic, offer to move to DM for details
4. If an action was taken (return initiated, ticket created), confirm it clearly.
5. If escalation is required, explain that a specialist will take over.
6. Never promise anything not backed by policy.
7. Include a suggested next action for the customer.

Respond with ONLY valid JSON:
{
  "response_text": "<the customer-facing response>",
  "confidence": <float 0.0-1.0>,
  "references_cited": ["<ref_id1>", "<ref_id2>"],
  "suggested_next_action": "<what customer should do next or null>",
  "internal_notes": "<any flags for quality review>"
}"""


def _build_context_prompt(state: AgentState) -> str:
    """Assembles all agent outputs into a prompt for response generation."""
    parts = []

    parts.append(f"Customer message: {state.get('message', '')}")
    parts.append(f"Channel: {state.get('channel', 'web')}")
    parts.append(f"Detected intent: {state.get('intent', 'unknown')}")
    parts.append(f"Sentiment: {state.get('sentiment', 'neutral')}")
    parts.append(f"Urgency: {state.get('urgency', 'medium')}")

    order_ctx = state.get("order_context", {})
    if order_ctx:
        parts.append(f"\nOrder Context:\n{json.dumps(order_ctx, indent=2, default=str)}")

    policy_snippets = state.get("policy_snippets", [])
    if policy_snippets:
        parts.append("\nApplicable Policies:")
        for p in policy_snippets:
            parts.append(f"  - [{p.get('reference_id', '')}] {p.get('rule', '')} (confidence: {p.get('confidence', 0)})")

    product_ctx = state.get("product_context", {})
    if product_ctx and product_ctx.get("comparison"):
        parts.append(f"\nProduct Information:\n{json.dumps(product_ctx, indent=2, default=str)}")

    action_result = state.get("action_result", {})
    if action_result:
        parts.append(f"\nAction Taken: {state.get('action_taken', 'none')}")
        parts.append(f"Result: {json.dumps(action_result, default=str)}")

    if state.get("escalation_required"):
        parts.append(f"\nESCALATION REQUIRED: {state.get('escalation_reason', '')}")
        parts.append(f"Routing to: {state.get('target_team', '')}")

    return "\n".join(parts)


def _generate_fallback_response(state: AgentState) -> dict | None:
    """
    Generate a helpful fallback response when data is missing.
    Returns None if no fallback is needed (data is available).
    """
    intent = state.get("intent", "")
    order_ctx = state.get("order_context", {})
    policy_snippets = state.get("policy_snippets", [])
    quality_issues = state.get("quality_issues", [])

    # Case 1: Order-related intent but no order data found
    if intent in ("order_tracking", "return_request", "refund_status", "delivery_complaint", "damaged_product"):
        if not order_ctx or not order_ctx.get("order_id"):
            return {
                "response_text": (
                    "I'd like to help you with that, but I wasn't able to locate your order. "
                    "Could you please share your order ID? It starts with 'SE' followed by numbers "
                    "(e.g., SE10234). You can find it in your order confirmation email or under "
                    "'My Orders' in your account."
                ),
                "confidence": 0.70,
                "references_cited": [],
                "suggested_next_action": "Please share your order ID so I can look up your details.",
                "internal_notes": "Fallback: order not found, requesting order ID from customer",
            }

    # Case 2: Policy-dependent intent but no policy matched
    if intent in ("return_request", "refund_status", "warranty", "coupon_issue") and not policy_snippets:
        return {
            "response_text": (
                "I want to give you accurate information, but I'm having trouble finding the "
                "specific policy for your situation. Let me connect you with a specialist who "
                "can review your case and provide the correct guidance. "
                "In the meantime, you can check our general policies at shopease.com/policies."
            ),
            "confidence": 0.60,
            "references_cited": [],
            "suggested_next_action": "A specialist will review your case for the exact policy details.",
            "internal_notes": "Fallback: no policy match found, suggesting specialist",
        }

    # Case 3: Agent errors detected in audit trail
    audit_trail = state.get("audit_trail", [])
    has_errors = any("ERROR" in entry.get("action", "") for entry in audit_trail)
    if has_errors:
        return {
            "response_text": (
                "I'm experiencing a temporary issue looking up your information. "
                "I apologize for the inconvenience. Please try again in a moment, "
                "or I can connect you with our support team who can help you directly."
            ),
            "confidence": 0.55,
            "references_cited": [],
            "suggested_next_action": "Please try again or say 'connect me to support' for human assistance.",
            "internal_notes": f"Fallback: agent errors detected in pipeline",
        }

    return None


def _mock_generate_response(state: AgentState) -> dict:
    """Rule-based response generation when no API key is available."""
    # Check if fallback is needed first
    fallback = _generate_fallback_response(state)
    if fallback:
        return fallback

    intent = state.get("intent", "")
    order_ctx = state.get("order_context", {})
    action_result = state.get("action_result", {})
    policy_snippets = state.get("policy_snippets", [])
    escalation_required = state.get("escalation_required", False)

    refs = [p.get("reference_id", "") for p in policy_snippets if p.get("reference_id")]

    if escalation_required:
        return {
            "response_text": f"I understand your concern. This requires specialist attention. I'm routing your case to our {state.get('target_team', 'support')} team who will reach out within 2 hours. Your reference number is {order_ctx.get('order_id', 'pending')}.",
            "confidence": 0.85,
            "references_cited": refs,
            "suggested_next_action": "Our specialist team will contact you shortly. No further action needed from your side.",
            "internal_notes": f"Escalated: {state.get('escalation_reason', '')}",
        }

    if intent == "order_tracking":
        shipment = order_ctx.get("shipment", {})
        return {
            "response_text": f"Your order {order_ctx.get('order_id', '')} is currently {shipment.get('status', 'processing')}. It's being shipped via {shipment.get('carrier', 'our delivery partner')} (tracking: {shipment.get('tracking', 'pending')}). Expected delivery: {shipment.get('eta', 'within 5-7 days')}.",
            "confidence": 0.92,
            "references_cited": refs,
            "suggested_next_action": "You can track your shipment using the tracking number above.",
            "internal_notes": "",
        }

    if intent == "return_request":
        if action_result.get("success"):
            return {
                "response_text": f"Your return has been initiated successfully! Return ID: {action_result.get('return_id', '')}. Pickup is scheduled for {action_result.get('pickup_date', 'within 3 days')}. Please keep the item in its original packaging.",
                "confidence": 0.90,
                "references_cited": refs,
                "suggested_next_action": "Please keep the product ready for pickup in original packaging.",
                "internal_notes": "",
            }
        return {
            "response_text": "I'd like to help with your return. Could you share your order ID so I can check eligibility?",
            "confidence": 0.75,
            "references_cited": refs,
            "suggested_next_action": "Share order ID to proceed.",
            "internal_notes": "",
        }

    if intent == "product_inquiry":
        product_ctx = state.get("product_context", {})
        recommendation = product_ctx.get("recommendation", "I can help you compare products.")
        return {
            "response_text": recommendation,
            "confidence": 0.88,
            "references_cited": [],
            "suggested_next_action": "Would you like more details on any specific product?",
            "internal_notes": "",
        }

    if intent == "coupon_issue":
        policy_text = policy_snippets[0]["rule"] if policy_snippets else "Coupon eligibility depends on cart value and category restrictions."
        return {
            "response_text": f"I've checked your coupon issue. {policy_text} Please verify that your cart meets the minimum value requirement and items are coupon-eligible.",
            "confidence": 0.87,
            "references_cited": refs,
            "suggested_next_action": "Try removing non-eligible items and re-applying the coupon.",
            "internal_notes": "",
        }

    if intent == "damaged_product":
        return {
            "response_text": f"I'm sorry to hear about the damaged product. A support ticket has been created ({action_result.get('ticket_id', 'pending')}). Our team will review your case and arrange a replacement or refund within 48 hours.",
            "confidence": 0.88,
            "references_cited": refs,
            "suggested_next_action": "Please upload photos of the damaged product for faster processing.",
            "internal_notes": "",
        }

    return {
        "response_text": "Thank you for reaching out. How can I help you today? I can assist with orders, returns, product information, and more.",
        "confidence": 0.70,
        "references_cited": [],
        "suggested_next_action": "Please describe your issue and I'll do my best to help.",
        "internal_notes": "Generic fallback response",
    }


def generate_response(state: AgentState) -> AgentState:
    """
    LangGraph node: generates the final customer-facing response.

    Reads: ALL state fields (message, intent, order_context, policy_snippets,
           product_context, action_result, escalation_required, channel)
    Writes: response_text, response_confidence, references_cited, suggested_next_action,
            agents_called, audit_trail
    """
    # Check for fallback scenarios FIRST (missing data, errors)
    fallback = _generate_fallback_response(state)
    if fallback:
        result = fallback
    elif USE_MOCK or not OPENAI_API_KEY:
        result = _mock_generate_response(state)
    else:
        try:
            llm = ChatOpenAI(
                model=OPENAI_MODEL,
                api_key=OPENAI_API_KEY,
                temperature=0.3,
            )
            context_prompt = _build_context_prompt(state)
            messages = [
                SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
                HumanMessage(content=context_prompt),
            ]
            response = llm.invoke(messages)
            result = json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            result = _mock_generate_response(state)

    return {
        "response_text": result.get("response_text", ""),
        "response_confidence": float(result.get("confidence", 0.5)),
        "references_cited": result.get("references_cited", []),
        "suggested_next_action": result.get("suggested_next_action", ""),
        "agents_called": ["response_generator"],
        "audit_trail": [{
            "agent": "response_generator",
            "action": "generate_response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"confidence={result.get('confidence', 0.5)}, refs={result.get('references_cited', [])}",
        }],
    }
