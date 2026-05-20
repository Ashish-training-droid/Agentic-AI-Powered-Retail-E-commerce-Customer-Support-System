"""
LangGraph Workflow Definition (Person 1)

This is the main orchestration graph that connects all agents into a
coherent pipeline. It defines:
- Nodes (each agent as a graph node)
- Edges (sequential and conditional routing between nodes)
- Entry/exit points

The graph represents the full customer support resolution flow.
"""

from __future__ import annotations
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END

from src.orchestrator.state import AgentState
from src.orchestrator.router import (
    route_after_intent,
    route_after_order,
    route_after_policy,
    route_after_risk,
)
from src.agents.intent_classifier import classify_intent
from src.agents.order_context import fetch_order_context
from src.agents.policy_retrieval import retrieve_policy
from src.agents.product_advisory import advise_product
from src.agents.workflow_automation import execute_workflow
from src.agents.escalation_risk import check_risk
from src.agents.response_generator import generate_response
from src.orchestrator.evaluator import evaluate_quality


def _escalate(state: AgentState) -> AgentState:
    """Terminal node for escalated cases — generates an escalation response."""
    return {
        "response_text": (
            f"Your case has been escalated to our {state.get('target_team', 'specialist')} team. "
            f"Reason: {state.get('escalation_reason', 'requires specialist attention')}. "
            f"Priority: {state.get('priority', 'P3')}. "
            f"A team member will contact you within 2 hours."
        ),
        "response_confidence": 0.95,
        "references_cited": [],
        "suggested_next_action": "Our specialist team will reach out to you shortly.",
        "agents_called": ["escalation_handler"],
        "audit_trail": [{
            "agent": "escalation_handler",
            "action": "escalate_to_human",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"team={state.get('target_team')}, priority={state.get('priority')}",
        }],
    }


def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph workflow.

    Flow:
    START -> classify_intent -> [route based on intent] ->
      -> fetch_order -> [route] -> retrieve_policy -> [route] -> execute_workflow
      -> evaluate_quality -> check_risk -> [generate_response | escalate] -> END
    """
    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("fetch_order", fetch_order_context)
    graph.add_node("retrieve_policy", retrieve_policy)
    graph.add_node("advise_product", advise_product)
    graph.add_node("execute_workflow", execute_workflow)
    graph.add_node("evaluate", evaluate_quality)
    graph.add_node("check_risk", check_risk)
    graph.add_node("generate_response", generate_response)
    graph.add_node("escalate", _escalate)

    # Entry point
    graph.add_edge(START, "classify_intent")

    # After intent classification — conditional routing
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "fetch_order": "fetch_order",
            "retrieve_policy": "retrieve_policy",
            "advise_product": "advise_product",
            "direct_response": "evaluate",
        },
    )

    # After order context — conditional routing
    graph.add_conditional_edges(
        "fetch_order",
        route_after_order,
        {
            "retrieve_policy": "retrieve_policy",
            "execute_workflow": "execute_workflow",
            "evaluate": "evaluate",
        },
    )

    # After policy retrieval — conditional routing
    graph.add_conditional_edges(
        "retrieve_policy",
        route_after_policy,
        {
            "execute_workflow": "execute_workflow",
            "evaluate": "evaluate",
        },
    )

    # Product advisory goes directly to evaluate
    graph.add_edge("advise_product", "evaluate")

    # Workflow automation goes to evaluate
    graph.add_edge("execute_workflow", "evaluate")

    # Evaluate goes to risk check
    graph.add_edge("evaluate", "check_risk")

    # After risk check — either generate response or escalate
    graph.add_conditional_edges(
        "check_risk",
        route_after_risk,
        {
            "generate_response": "generate_response",
            "escalate": "escalate",
        },
    )

    # Terminal nodes
    graph.add_edge("generate_response", END)
    graph.add_edge("escalate", END)

    return graph


def compile_graph():
    """Build and compile the graph for execution."""
    graph = build_graph()
    return graph.compile()


# Pre-compiled graph instance for import
app = compile_graph()
