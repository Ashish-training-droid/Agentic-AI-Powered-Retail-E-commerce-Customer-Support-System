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


# Priority-ordered keyword groups. Earlier groups win.
# (more specific intents at the top so "MacBook is lost" doesn't fall through.)
MOCK_KEYWORD_GROUPS = [
    ("damaged_product",   ["cracked", "broken", "damaged", "damage", "defective", "not working", "doa", "arrived broken"],
                          {"sentiment": "angry", "urgency": "critical", "confidence": 0.93}),
    ("delivery_complaint",["lost", "missing", "never arrived", "not delivered", "no update", "stuck in transit"],
                          {"sentiment": "negative", "urgency": "high", "confidence": 0.90}),
    ("coupon_issue",      ["coupon", "promo", "discount code", "voucher", "save20", "festive10"],
                          {"sentiment": "negative", "urgency": "medium", "confidence": 0.91}),
    ("refund_status",     ["refund", "money back", "credited", "haven't received my refund", "havent received my refund"],
                          {"sentiment": "negative", "urgency": "high", "confidence": 0.88}),
    ("return_request",    ["return", "send back", "give back", "exchange"],
                          {"sentiment": "neutral", "urgency": "medium", "confidence": 0.90}),
    ("warranty",          ["warranty", "guarantee", "covered under"],
                          {"sentiment": "neutral", "urgency": "medium", "confidence": 0.87}),
    ("product_inquiry",   ["compare", "which is better", "recommend", "suggest", "vs ", " vs.", "difference between",
                           "best laptop", "best phone", "product comparison"],
                          {"sentiment": "positive", "urgency": "low", "confidence": 0.95}),
    ("order_tracking",    ["where is my order", "track my", "track order", "delivery", "shipped", "arrive",
                           "eta", "out for delivery", "where is", "hasn't arrived", "hasnt arrived"],
                          {"sentiment": "neutral", "urgency": "medium", "confidence": 0.92}),
]

# Sentiment override words — escalate sentiment if these appear.
_ANGRY_WORDS = ["unacceptable", "ridiculous", "appalling", "worst", "terrible",
                "extremely frustrated", "fed up", "never again"]
_FRUSTRATED_WORDS = ["frustrated", "disappointed", "annoying", "annoyed", "upset"]


def _mock_classify(message: str) -> dict:
    """Rule-based fallback when USE_MOCK=true or no API key.

    Priority-ordered keyword matching so 'MacBook is lost' classifies as
    delivery_complaint and 'cracked screen' classifies as damaged_product,
    instead of both falling through to general_faq.
    """
    message_lower = message.lower()

    matched_intent = None
    matched_meta: dict = {}
    for intent_name, keywords, meta in MOCK_KEYWORD_GROUPS:
        if any(kw in message_lower for kw in keywords):
            matched_intent = intent_name
            matched_meta = dict(meta)
            break

    if not matched_intent:
        return {
            "intent": "general_faq",
            "sub_intent": None,
            "sentiment": "neutral",
            "urgency": "low",
            "confidence": 0.75,
        }

    # Sentiment override based on emotional words
    if any(w in message_lower for w in _ANGRY_WORDS):
        matched_meta["sentiment"] = "angry"
        matched_meta["urgency"] = "critical"
    elif any(w in message_lower for w in _FRUSTRATED_WORDS) and matched_meta.get("sentiment") == "neutral":
        matched_meta["sentiment"] = "negative"
        if matched_meta.get("urgency") == "low":
            matched_meta["urgency"] = "medium"

    matched_meta["intent"] = matched_intent
    matched_meta["sub_intent"] = None
    return matched_meta


def classify_intent(state: AgentState) -> AgentState:
    """
    LangGraph node: classifies customer intent from the message.

    Reads: message, channel, conversation_history
    Writes: intent, sub_intent, sentiment, urgency, intent_confidence, agents_called, audit_trail
    """
    message = state.get("message", "")
    channel = state.get("channel", "web")

    # Handle empty or very short messages
    if not message or len(message.strip()) < 3:
        result = {
            "intent": "general_faq",
            "sub_intent": None,
            "sentiment": "neutral",
            "urgency": "low",
            "confidence": 0.2,
        }
    elif USE_MOCK or not OPENAI_API_KEY:
        result = _mock_classify(message)
    else:
        try:
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
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = _mock_classify(message)
        except Exception:
            # API timeout, rate limit, network error — fall back to rule-based
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
