"""
Router / Orchestration Logic (Person 1)

Determines which agents to invoke based on the classified intent.
This is the "brain" that decides the workflow path through the agent graph.

Includes:
- Confidence-based routing (clarify if unsure)
- Missing data detection (skip agents if data isn't available)
- Graceful fallbacks (never crash, always give a helpful response)
"""

from __future__ import annotations
from typing import Literal

from src.orchestrator.state import AgentState
from src.config import CONFIDENCE_THRESHOLD_PROCEED, CONFIDENCE_THRESHOLD_LOW
from src.utils.validators import extract_order_id_from_message


# Intent-to-agent routing table
ROUTING_TABLE: dict[str, list[str]] = {
    "order_tracking": ["order_context"],
    "return_request": ["order_context", "policy_retrieval", "workflow_automation"],
    "refund_status": ["order_context", "policy_retrieval"],
    "product_inquiry": ["product_advisory"],
    "warranty": ["order_context", "policy_retrieval"],
    "coupon_issue": ["policy_retrieval"],
    "delivery_complaint": ["order_context", "policy_retrieval"],
    "damaged_product": ["order_context", "policy_retrieval", "workflow_automation"],
    "general_faq": [],
}

# Intents that STRICTLY require an order ID (skip if missing)
ORDER_ID_STRICT_INTENTS = {
    "order_tracking",
    "refund_status",
}

# Intents that benefit from order context but can try customer_id lookup
ORDER_ID_PREFERRED_INTENTS = {
    "return_request",
    "delivery_complaint",
    "damaged_product",
}


def determine_route(state: AgentState) -> list[str]:
    """
    Given the current state (after intent classification), returns the list
    of agents that should be invoked.
    """
    intent = state.get("intent", "general_faq")
    return ROUTING_TABLE.get(intent, [])


def _has_order_id(state: AgentState) -> bool:
    """Check if we have an order ID from state or extractable from message."""
    if state.get("order_id"):
        return True
    message = state.get("message", "")
    return extract_order_id_from_message(message) is not None


def _is_low_confidence(state: AgentState) -> bool:
    """Check if intent confidence is too low to proceed."""
    return state.get("intent_confidence", 0.0) < CONFIDENCE_THRESHOLD_LOW


def _is_moderate_confidence(state: AgentState) -> bool:
    """Check if intent confidence is in the uncertain zone."""
    conf = state.get("intent_confidence", 0.0)
    return CONFIDENCE_THRESHOLD_LOW <= conf < CONFIDENCE_THRESHOLD_PROCEED


def needs_order_context(state: AgentState) -> bool:
    """Check if the current intent requires order context retrieval."""
    agents = determine_route(state)
    return "order_context" in agents


def needs_policy(state: AgentState) -> bool:
    """Check if the current intent requires policy retrieval."""
    agents = determine_route(state)
    return "policy_retrieval" in agents


def needs_product(state: AgentState) -> bool:
    """Check if the current intent requires product advisory."""
    agents = determine_route(state)
    return "product_advisory" in agents


def needs_workflow(state: AgentState) -> bool:
    """Check if the current intent requires workflow automation."""
    agents = determine_route(state)
    return "workflow_automation" in agents


def route_after_intent(state: AgentState) -> Literal[
    "fetch_order", "retrieve_policy", "advise_product", "direct_response", "clarify"
]:
    """
    LangGraph conditional edge: decides the first context-gathering step.

    Confidence-based routing:
    - confidence < 0.4 → "clarify" (ask customer to rephrase)
    - confidence >= 0.4 → proceed with normal routing

    Data availability checks:
    - If order_context needed but no order ID available → skip to direct_response
      (response generator will ask for the order ID)
    """
    # Very low confidence — ask customer to clarify
    if _is_low_confidence(state):
        return "clarify"

    agents = determine_route(state)
    intent = state.get("intent", "general_faq")

    # If order context needed, check if we have enough info to look it up
    if "order_context" in agents:
        if _has_order_id(state):
            # Have an explicit order ID — definitely fetch
            return "fetch_order"
        elif intent in ORDER_ID_STRICT_INTENTS and not state.get("customer_id"):
            # Strict intents with no order ID and no customer ID — ask for info
            return "direct_response"
        else:
            # Try fetching by customer_id (may find their recent order)
            return "fetch_order"
    elif "policy_retrieval" in agents:
        return "retrieve_policy"
    elif "product_advisory" in agents:
        return "advise_product"
    else:
        return "direct_response"


def route_after_order(state: AgentState) -> Literal[
    "retrieve_policy", "execute_workflow", "evaluate"
]:
    """
    LangGraph conditional edge: after fetching order context, decide next step.

    If order_context came back empty (not found), skip downstream agents
    that depend on it and go straight to evaluate.
    """
    agents = determine_route(state)
    order_context = state.get("order_context", {})

    # If order was not found, don't try policy/workflow that depends on it
    if not order_context or not order_context.get("order_id"):
        return "evaluate"

    if "policy_retrieval" in agents:
        return "retrieve_policy"
    elif "workflow_automation" in agents:
        return "execute_workflow"
    else:
        return "evaluate"


def route_after_policy(state: AgentState) -> Literal["execute_workflow", "evaluate"]:
    """
    LangGraph conditional edge: after policy retrieval, decide next step.

    Only proceed to workflow if policy confirms eligibility.
    """
    agents = determine_route(state)
    policy_snippets = state.get("policy_snippets", [])

    if "workflow_automation" in agents:
        # Only execute workflow if we have policy backing
        if policy_snippets or state.get("intent") == "damaged_product":
            return "execute_workflow"
        else:
            return "evaluate"
    else:
        return "evaluate"


def route_after_risk(state: AgentState) -> Literal["generate_response", "await_approval", "escalate"]:
    """
    LangGraph conditional edge: after risk check, route to one of three terminals.

    Bands (set by ``src.agents.escalation_risk``):
        * "escalate"           -> hand off to ``escalate`` terminal (no AI response served)
        * "approval_required"  -> generate draft, then ``await_approval`` (HITL queue)
        * "auto" / unset       -> generate response and serve directly

    ``escalation_required`` is kept for backwards compatibility — any agent
    that sets it forces the escalate path even if ``risk_band`` was not set.
    """
    if state.get("escalation_required", False):
        return "escalate"
    if str(state.get("risk_band") or "").lower() == "approval_required":
        return "await_approval"
    return "generate_response"


def route_after_response(state: AgentState) -> Literal["await_approval", "end"]:
    """LangGraph conditional edge after response generation.

    If risk decided we need human approval, the freshly-drafted response is
    parked in the approval queue instead of being served to the customer.
    """
    if str(state.get("risk_band") or "").lower() == "approval_required":
        return "await_approval"
    return "end"
