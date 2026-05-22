import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Get a secret from environment, .env file, or Streamlit secrets (for cloud)."""
    value = os.getenv(key, "")
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
OPENAI_MODEL = _get_secret("OPENAI_MODEL", "gpt-4o")
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

CONFIDENCE_THRESHOLD_PROCEED = 0.7
CONFIDENCE_THRESHOLD_LOW = 0.4
POLICY_MATCH_THRESHOLD = 0.8
RESPONSE_CONFIDENCE_SERVE = 0.75
RESPONSE_CONFIDENCE_DRAFT = 0.5

SUPPORTED_INTENTS = [
    "order_tracking",
    "return_request",
    "refund_status",
    "product_inquiry",
    "warranty",
    "coupon_issue",
    "delivery_complaint",
    "damaged_product",
    "general_faq",
]

SUPPORTED_SENTIMENTS = ["positive", "neutral", "negative", "angry"]
SUPPORTED_URGENCY = ["low", "medium", "high", "critical"]
SUPPORTED_CHANNELS = ["web", "mobile", "email", "social", "portal"]
