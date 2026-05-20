"""
Formatting utilities for display, responses, and data normalization.
"""

from __future__ import annotations
from datetime import datetime, timezone


def format_currency(amount: float | int, currency: str = "INR") -> str:
    """
    Format amount as currency string.

    Args:
        amount: Numeric amount
        currency: Currency code (default INR)

    Returns:
        Formatted string like "Rs 2,499" or "$24.99"
    """
    if currency == "INR":
        return f"Rs {amount:,.0f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    return f"{currency} {amount:,.2f}"


def format_timestamp(iso_string: str | None, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    """
    Convert ISO timestamp to human-readable format.

    Args:
        iso_string: ISO 8601 timestamp string
        fmt: Output format (default: "20 May 2026, 02:30 PM")

    Returns:
        Formatted date string or "N/A" if input is None
    """
    if not iso_string:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except (ValueError, AttributeError):
        return iso_string


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to max_length, adding suffix if truncated.

    Args:
        text: Input text
        max_length: Maximum character length
        suffix: String to append when truncated

    Returns:
        Truncated or original text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_agent_chain(agents: list[str], separator: str = " -> ") -> str:
    """
    Format agent call chain for display.

    Args:
        agents: List of agent names in call order
        separator: String between agents

    Returns:
        Formatted chain like "intent_classifier -> order_context -> response_generator"
    """
    return separator.join(agents)


def format_order_summary(order_context: dict) -> str:
    """
    Create a one-line order summary for logs and agent-assist view.

    Args:
        order_context: Order data dictionary

    Returns:
        Summary string like "SE10234 | shipped | Rs 2,499 | BlueDart"
    """
    if not order_context:
        return "No order data"

    parts = [
        order_context.get("order_id", "N/A"),
        order_context.get("status", "unknown"),
        format_currency(order_context.get("payment", {}).get("amount", 0)),
        order_context.get("shipment", {}).get("carrier", "N/A"),
    ]
    return " | ".join(parts)


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data like card numbers or tokens.

    Args:
        text: Sensitive string to mask
        visible_chars: Number of chars to leave visible at end

    Returns:
        Masked string like "****7890"
    """
    if len(text) <= visible_chars:
        return "*" * len(text)
    return "*" * (len(text) - visible_chars) + text[-visible_chars:]
