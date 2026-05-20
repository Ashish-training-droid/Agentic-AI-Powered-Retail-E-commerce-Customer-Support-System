"""
Session management utilities.

Handles session creation, initial state construction, and
conversation history tracking.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone

from src.orchestrator.state import AgentState
from src.utils.validators import sanitize_user_input, extract_order_id_from_message


def generate_session_id() -> str:
    """Generate a unique session identifier."""
    return f"sess_{uuid.uuid4().hex[:12]}"


def build_initial_state(
    message: str,
    customer_id: str = "",
    channel: str = "web",
    session_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> AgentState:
    """
    Construct the initial AgentState for a new customer message.

    This is the entry point for every conversation turn. It sanitizes
    input, extracts order IDs if present, and prepares the state dict
    for the LangGraph pipeline.

    Args:
        message: Customer's raw message
        customer_id: Customer identifier
        channel: Communication channel (web/mobile/email/social/portal)
        session_id: Optional existing session ID (generates new if None)
        conversation_history: Previous messages in this session

    Returns:
        AgentState dict ready for graph.invoke()
    """
    clean_message = sanitize_user_input(message)
    order_id = extract_order_id_from_message(clean_message)

    state: AgentState = {
        "session_id": session_id or generate_session_id(),
        "customer_id": customer_id,
        "channel": channel,
        "message": clean_message,
        "conversation_history": conversation_history or [],
    }

    if order_id:
        state["order_id"] = order_id

    return state


def append_to_history(
    history: list[dict],
    role: str,
    content: str,
    metadata: dict | None = None,
) -> list[dict]:
    """
    Append a message to conversation history.

    Args:
        history: Existing conversation history
        role: "customer" or "assistant"
        content: Message text
        metadata: Optional metadata (intent, confidence, etc.)

    Returns:
        Updated history list
    """
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        entry["metadata"] = metadata
    history.append(entry)
    return history
