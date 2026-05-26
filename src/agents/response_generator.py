"""
Response Generation Agent (Ashish (Person 1) + Aditi (Person 4))

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


RESPONSE_SYSTEM_PROMPT = """You are ShopEase's AI customer support assistant. You speak like a helpful, empathetic human — not a robot.

Your job: write a natural, warm response that solves the customer's problem using the context and data provided.

CRITICAL RULES:
- NEVER respond with generic messages like "How can I help you?" or "Thank you for reaching out."
- ALWAYS use the specific data provided (order IDs, carrier names, dates, amounts, policy details).
- If you have order context, USE IT. If you have policy snippets, CITE THEM.
- Every response must contain at least ONE specific detail from the provided context.

Guidelines:
1. Be NATURAL and conversational. Sound like a friendly support agent, not a template.
2. Use the actual data: mention order IDs, carrier names, dates, amounts when available.
3. If a policy applies, weave it naturally into the response and cite the reference like [POL-RET-FASH-001].
4. Show empathy for frustration: "I completely understand how frustrating this must be..."
5. Be specific: don't say "your order is on the way" — say "Your order SE10234 is with BlueDart, tracking BD987120234, arriving May 22."
6. If data is missing, ask for it politely and explain WHY you need it (e.g., "Could you share your order ID so I can look up the exact delivery status?").
7. If an action was taken (return initiated, ticket created), confirm with clear details (IDs, dates).
8. Adapt tone to channel:
   - web/mobile: friendly, concise, 2-3 short paragraphs max
   - email: slightly more formal with greeting
   - social: brief, empathetic
9. Always end with a clear next step for the customer.
10. Use conversation history to maintain context across messages.

EXAMPLES OF GOOD RESPONSES:

Example 1 (order_tracking):
Customer: "Where is my order SE10234?"
Context: order shipped, BlueDart, tracking BD987120234, ETA May 22
Response: "Hi! I checked on your order SE10234 — it's currently in transit with BlueDart (tracking: BD987120234) and expected to arrive on May 22. I notice it was supposed to arrive yesterday, so apologies for the slight delay. You can track it in real-time using the tracking number above. If it doesn't arrive by the updated ETA, we'll automatically process a shipping fee refund for you. [POL-DEL-DELAY-001]"

Example 2 (return_request):
Customer: "I want to return my shoes"
Context: order SE10567, Nike Air shoes, Rs 8999, delivered 3 days ago, fashion 15-day return policy
Response: "I'd be happy to help with that return! I found your order SE10567 — Nike Air Running Shoes (Rs 8,999), delivered 3 days ago. Great news: fashion items can be returned within 15 days if unworn with original tags attached [POL-RET-FASH-001]. Since you're well within the window, I've gone ahead and initiated your return. Pickup is scheduled for May 23 — please keep the shoes in their original box with tags on. You'll receive your refund within 5-7 business days after pickup."

Example 3 (damaged_product):
Customer: "My phone arrived with a cracked screen!"
Context: SE10890, Samsung Galaxy S24, Rs 74999, VIP customer, damage policy applies
Response: "I'm so sorry about this — receiving a damaged Rs 74,999 phone is completely unacceptable, and I understand your frustration. I've immediately flagged your order SE10890 for our replacement team. As per our policy, damaged products reported within 48 hours qualify for a free replacement or full refund [POL-GEN-DMG-001]. To speed things up, could you upload photos of the cracked screen via 'My Orders' > 'SE10890' > 'Report Issue'? A specialist will reach out within 2 hours to arrange your replacement."

Respond with ONLY valid JSON:
{
  "response_text": "<natural, helpful customer response>",
  "confidence": <float 0.0-1.0>,
  "references_cited": ["<ref_id1>", "<ref_id2>"],
  "suggested_next_action": "<clear next step for the customer>",
  "internal_notes": "<any flags for quality review>"
}"""


def _build_context_prompt(state: AgentState) -> str:
    """Assembles all agent outputs into a prompt for response generation."""
    parts = []

    # Include conversation history for context-aware responses
    conversation_history = state.get("conversation_history", [])
    if conversation_history:
        parts.append("Conversation history:")
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"  {role}: {content}")
        parts.append("")

    parts.append(f"Current customer message: {state.get('message', '')}")
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
        ticket = action_result.get("ticket_id") or action_result.get("reference_ticket") or "pending"
        policy_text = policy_snippets[0]["rule"] if policy_snippets else "Damaged items must be reported within 48 hours with photo evidence."
        return {
            "response_text": f"I'm very sorry about the damaged product. {policy_text} A support ticket ({ticket}) has been created. Our team will review your case and arrange a replacement or full refund within 48 hours.",
            "confidence": 0.88,
            "references_cited": refs,
            "suggested_next_action": "Please upload photos of the damaged product via 'My Orders' for faster processing.",
            "internal_notes": "",
        }

    if intent == "delivery_complaint":
        shipment = order_ctx.get("shipment", {})
        policy_text = policy_snippets[0]["rule"] if policy_snippets else "If delivery is delayed beyond 3 days of estimated date, you are eligible for a shipping fee refund."
        status = shipment.get("status", "unknown")
        eta = shipment.get("eta", "unknown")
        return {
            "response_text": f"I understand your delivery concern. Your shipment status is currently '{status}'. {policy_text} Expected delivery: {eta}. If it doesn't arrive by then, we'll automatically process compensation.",
            "confidence": 0.87,
            "references_cited": refs,
            "suggested_next_action": "If the order doesn't arrive by the updated ETA, contact us for shipping fee refund.",
            "internal_notes": "",
        }

    if intent == "refund_status":
        policy_text = policy_snippets[0]["rule"] if policy_snippets else "Refunds are processed within 5-7 business days after return pickup."
        payment_method = order_ctx.get("payment", {}).get("method", "your original payment method")
        return {
            "response_text": f"Regarding your refund: {policy_text} Your refund will be credited to {payment_method}. You can check the latest status under 'My Orders' > 'Refund Status'.",
            "confidence": 0.88,
            "references_cited": refs,
            "suggested_next_action": "Check 'My Orders' for real-time refund status. UPI/wallet refunds are usually faster (24 hours).",
            "internal_notes": "",
        }

    if intent == "warranty":
        policy_text = policy_snippets[0]["rule"] if policy_snippets else "Electronics carry 1-year manufacturer warranty from date of delivery."
        return {
            "response_text": f"About your warranty query: {policy_text} To claim warranty, please visit the brand's authorized service center with your ShopEase invoice. We can email you a copy if needed.",
            "confidence": 0.87,
            "references_cited": refs,
            "suggested_next_action": "Would you like us to email your invoice or help locate the nearest service center?",
            "internal_notes": "",
        }

    return {
        "response_text": "Thank you for reaching out! I can help you with orders, returns, refunds, product comparisons, and more. What would you like help with?",
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
    if USE_MOCK or not OPENAI_API_KEY:
        # Mock mode: use fallback checks + template responses
        fallback = _generate_fallback_response(state)
        result = fallback if fallback else _mock_generate_response(state)
    else:
        # LIVE mode: always use OpenAI for natural responses
        try:
            llm = ChatOpenAI(
                model=OPENAI_MODEL,
                api_key=OPENAI_API_KEY,
                temperature=0.4,
            )
            context_prompt = _build_context_prompt(state)
            messages = [
                SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
                HumanMessage(content=context_prompt),
            ]
            response = llm.invoke(messages)
            result = json.loads(response.content)
        except (json.JSONDecodeError, Exception):
            fallback = _generate_fallback_response(state)
            result = fallback if fallback else _mock_generate_response(state)

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
