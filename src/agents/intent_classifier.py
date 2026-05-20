"""
Intent Classification Agent (Person 1)

Classifies the customer message into one of 9 supported intents, detects
sentiment, urgency level, and outputs a confidence score.

Uses OpenAI function calling for structured extraction.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import OPENAI_API_KEY, OPENAI_MODEL, USE_MOCK, SUPPORTED_INTENTS
from src.orchestrator.state import AgentState


INTENT_SYSTEM_PROMPT = """You are an intent classification agent for ShopEase, a retail & e-commerce company.

Analyze the customer message and extract:
1. intent - the primary customer goal
2. sentiment - emotional tone of the message
3. urgency - how time-sensitive the request is
4. confidence - your confidence in the classification (0.0 to 1.0)

Supported intents:
- order_tracking: customer wants to know where their order is, delivery status
- return_request: customer wants to return or exchange a product
- refund_status: customer asking about refund timeline or status
- product_inquiry: customer comparing products, asking about specs/availability
- warranty: customer asking about warranty coverage or claims
- coupon_issue: coupon not applied, discount not working
- delivery_complaint: late delivery, wrong address, delivery failed
- damaged_product: received broken, defective, or wrong item
- general_faq: general questions about store, account, payment methods

Sentiment options: positive, neutral, negative, angry
Urgency options: low, medium, high, critical

Respond with ONLY valid JSON matching this exact schema:
{
  "intent": "<intent>",
  "sub_intent": "<optional sub-category or null>",
  "sentiment": "<sentiment>",
  "urgency": "<urgency>",
  "confidence": <float 0.0-1.0>
}"""


MOCK_RESPONSES = {
    "order": {"intent": "order_tracking", "sub_intent": None, "sentiment": "neutral", "urgency": "medium", "confidence": 0.92},
    "return": {"intent": "return_request", "sub_intent": None, "sentiment": "neutral", "urgency": "medium", "confidence": 0.90},
    "refund": {"intent": "refund_status", "sub_intent": None, "sentiment": "negative", "urgency": "high", "confidence": 0.88},
    "product": {"intent": "product_inquiry", "sub_intent": None, "sentiment": "positive", "urgency": "low", "confidence": 0.95},
    "warranty": {"intent": "warranty", "sub_intent": None, "sentiment": "neutral", "urgency": "medium", "confidence": 0.87},
    "coupon": {"intent": "coupon_issue", "sub_intent": None, "sentiment": "negative", "urgency": "medium", "confidence": 0.91},
    "deliver": {"intent": "delivery_complaint", "sub_intent": None, "sentiment": "negative", "urgency": "high", "confidence": 0.89},
    "damage": {"intent": "damaged_product", "sub_intent": None, "sentiment": "angry", "urgency": "critical", "confidence": 0.93},
    "broken": {"intent": "damaged_product", "sub_intent": None, "sentiment": "angry", "urgency": "critical", "confidence": 0.93},
}


def _mock_classify(message: str) -> dict:
    """Rule-based fallback when USE_MOCK=true or no API key."""
    message_lower = message.lower()
    for keyword, result in MOCK_RESPONSES.items():
        if keyword in message_lower:
            return result
    return {
        "intent": "general_faq",
        "sub_intent": None,
        "sentiment": "neutral",
        "urgency": "low",
        "confidence": 0.75,
    }


def classify_intent(state: AgentState) -> AgentState:
    """
    LangGraph node: classifies customer intent from the message.

    Reads: message, channel, conversation_history
    Writes: intent, sub_intent, sentiment, urgency, intent_confidence, agents_called, audit_trail
    """
    message = state.get("message", "")
    channel = state.get("channel", "web")

    if USE_MOCK or not OPENAI_API_KEY:
        result = _mock_classify(message)
    else:
        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.0,
        )
        messages = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=f"Channel: {channel}\nCustomer message: {message}"),
        ]
        response = llm.invoke(messages)
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = _mock_classify(message)

    intent = result.get("intent", "general_faq")
    if intent not in SUPPORTED_INTENTS:
        intent = "general_faq"

    return {
        "intent": intent,
        "sub_intent": result.get("sub_intent") or "",
        "sentiment": result.get("sentiment", "neutral"),
        "urgency": result.get("urgency", "medium"),
        "intent_confidence": float(result.get("confidence", 0.5)),
        "agents_called": ["intent_classifier"],
        "audit_trail": [{
            "agent": "intent_classifier",
            "action": "classify_intent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"intent={intent}, confidence={result.get('confidence', 0.5)}",
        }],
    }
