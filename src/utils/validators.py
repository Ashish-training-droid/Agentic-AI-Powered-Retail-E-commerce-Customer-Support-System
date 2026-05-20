"""
Input validation utilities for the support system.

Validates customer inputs, order IDs, and agent outputs
to catch bad data before it flows through the pipeline.
"""

from __future__ import annotations
import re

from src.config import SUPPORTED_INTENTS, SUPPORTED_SENTIMENTS, SUPPORTED_URGENCY, SUPPORTED_CHANNELS


ORDER_ID_PATTERN = re.compile(r"^SE\d{4,6}$")
CUSTOMER_ID_PATTERN = re.compile(r"^CUST_\d{4,6}$")


def validate_order_id(order_id: str) -> tuple[bool, str]:
    """
    Validate order ID format (SE followed by 4-6 digits).

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not order_id:
        return False, "Order ID is empty"
    if not ORDER_ID_PATTERN.match(order_id):
        return False, f"Invalid order ID format: '{order_id}'. Expected format: SE10234"
    return True, ""


def validate_customer_id(customer_id: str) -> tuple[bool, str]:
    """
    Validate customer ID format (CUST_ followed by 4-6 digits).

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not customer_id:
        return False, "Customer ID is empty"
    if not CUSTOMER_ID_PATTERN.match(customer_id):
        return False, f"Invalid customer ID format: '{customer_id}'. Expected format: CUST_1001"
    return True, ""


def validate_intent(intent: str) -> tuple[bool, str]:
    """
    Validate that the classified intent is in the supported list.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not intent:
        return False, "Intent is empty"
    if intent not in SUPPORTED_INTENTS:
        return False, f"Unsupported intent: '{intent}'. Supported: {SUPPORTED_INTENTS}"
    return True, ""


def validate_sentiment(sentiment: str) -> tuple[bool, str]:
    """Validate sentiment value."""
    if sentiment not in SUPPORTED_SENTIMENTS:
        return False, f"Invalid sentiment: '{sentiment}'. Supported: {SUPPORTED_SENTIMENTS}"
    return True, ""


def validate_urgency(urgency: str) -> tuple[bool, str]:
    """Validate urgency value."""
    if urgency not in SUPPORTED_URGENCY:
        return False, f"Invalid urgency: '{urgency}'. Supported: {SUPPORTED_URGENCY}"
    return True, ""


def validate_channel(channel: str) -> tuple[bool, str]:
    """Validate channel value."""
    if channel not in SUPPORTED_CHANNELS:
        return False, f"Invalid channel: '{channel}'. Supported: {SUPPORTED_CHANNELS}"
    return True, ""


def validate_confidence(confidence: float) -> tuple[bool, str]:
    """Validate confidence score is between 0 and 1."""
    if not isinstance(confidence, (int, float)):
        return False, f"Confidence must be numeric, got: {type(confidence)}"
    if confidence < 0.0 or confidence > 1.0:
        return False, f"Confidence must be between 0.0 and 1.0, got: {confidence}"
    return True, ""


def sanitize_user_input(message: str, max_length: int = 2000) -> str:
    """
    Sanitize user input to prevent injection and limit size.

    Args:
        message: Raw user message
        max_length: Maximum allowed character count

    Returns:
        Cleaned message string
    """
    if not message:
        return ""
    message = message.strip()
    message = message[:max_length]
    message = re.sub(r"[<>{}]", "", message)
    return message


def extract_order_id_from_message(message: str) -> str | None:
    """
    Attempt to extract an order ID from a customer message.

    Args:
        message: Customer's raw message

    Returns:
        Extracted order ID or None
    """
    match = re.search(r"SE\d{4,6}", message, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None
