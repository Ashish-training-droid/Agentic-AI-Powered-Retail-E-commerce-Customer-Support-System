"""
Router / Orchestration Logic (Person 1)

Determines which agents to invoke based on the classified intent.
This is the "brain" that decides the workflow path through the agent graph.
"""

from __future__ import annotations
from typing import Literal

from src.orchestrator.state import AgentState


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


def determine_route(state: AgentState) -> list[str]:
    """
    Given the current state (after intent classification), returns the list
    of agents that should be invoked.
    """
    intent = state.get("intent", "general_faq")
    return ROUTING_TABLE.get(intent, [])


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
    "fetch_order", "retrieve_policy", "advise_product", "direct_response"
]:
    """
    LangGraph conditional edge: decides the first context-gathering step.

    Priority order:
    1. If order context needed -> fetch_order (policy/workflow will follow)
    2. If only policy needed -> retrieve_policy
    3. If product inquiry -> advise_product
    4. Otherwise -> direct_response (skip to response generation)
    """
    agents = determine_route(state)

    if "order_context" in agents:
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
    """
    agents = determine_route(state)

    if "policy_retrieval" in agents:
        return "retrieve_policy"
    elif "workflow_automation" in agents:
        return "execute_workflow"
    else:
        return "evaluate"


def route_after_policy(state: AgentState) -> Literal["execute_workflow", "evaluate"]:
    """
    LangGraph conditional edge: after policy retrieval, decide next step.
    """
    agents = determine_route(state)

    if "workflow_automation" in agents:
        return "execute_workflow"
    else:
        return "evaluate"


def route_after_risk(state: AgentState) -> Literal["generate_response", "escalate"]:
    """
    LangGraph conditional edge: after risk check, either generate response or escalate.
    """
    if state.get("escalation_required", False):
        return "escalate"
    return "generate_response"
