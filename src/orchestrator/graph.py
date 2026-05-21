"""
LangGraph Workflow Definition (Person 1)

This is the main orchestration graph that connects all agents into a
coherent pipeline. Includes:
- Error-safe wrappers (agents never crash the pipeline)
- Clarification node (asks customer to rephrase if confidence is low)
- Graceful degradation at every step
"""

from __future__ import annotations
import traceback
from datetime import datetime, timezone
from functools import wraps
from typing import Callable

from langgraph.graph import StateGraph, START, END

from src.orchestrator.state import AgentState
from src.orchestrator.router import (
    route_after_intent,
    route_after_order,
    route_after_policy,
    route_after_response,
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
from src.governance.approval_queue import submit_for_approval
from src.governance.audit import build_audit_entry_from_state, save_audit_log


def error_safe(agent_name: str):
    """
    Decorator that wraps agent nodes to catch exceptions gracefully.

    If an agent throws an error, the pipeline continues with:
    - Error logged in audit trail
    - Empty/default outputs for that agent
    - Quality score will be reduced by evaluator
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: AgentState) -> AgentState:
            try:
                return func(state)
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)[:200]}"
                return {
                    "agents_called": [f"{agent_name}(ERROR)"],
                    "audit_trail": [{
                        "agent": agent_name,
                        "action": "ERROR",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "details": error_msg,
                    }],
                }
        return wrapper
    return decorator


def _clarify(state: AgentState) -> AgentState:
    """
    Clarification node — triggered when intent confidence is too low.

    Instead of guessing wrong, asks the customer to provide more details.
    """
    intent = state.get("intent", "unknown")
    confidence = state.get("intent_confidence", 0.0)

    clarification_messages = {
        "order_tracking": "I'd like to help you track your order. Could you share your order ID? It starts with 'SE' followed by numbers (e.g., SE10234).",
        "return_request": "I can help with returns. Could you tell me which product you'd like to return and share your order ID?",
        "product_inquiry": "I'd love to help you find the right product. Could you tell me what category you're looking at and what you'll use it for?",
        "general_faq": "I want to make sure I help you correctly. Could you provide a bit more detail about what you need?",
    }

    default_msg = (
        "I want to make sure I understand your request correctly. "
        "Could you provide a bit more detail? For example:\n"
        "- If it's about an order, share your order ID (starts with SE)\n"
        "- If it's about a product, tell me which product or category\n"
        "- If it's about a return or refund, mention the item and order"
    )

    response_text = clarification_messages.get(intent, default_msg)

    return {
        "response_text": response_text,
        "response_confidence": 0.60,
        "references_cited": [],
        "suggested_next_action": "Please provide more details so I can assist you better.",
        "quality_score": 0.5,
        "quality_issues": [f"Low classification confidence ({confidence:.2f}), requested clarification"],
        "agents_called": ["clarification_handler"],
        "audit_trail": [{
            "agent": "clarification_handler",
            "action": "request_clarification",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"confidence={confidence:.2f}, intent_guess={intent}",
        }],
    }


def _escalate(state: AgentState) -> AgentState:
    """Terminal node for escalated cases — generates an escalation response.

    Person 5 wires the audit log here so every escalation is durably recorded
    even when the response generator is skipped.
    """
    update: dict = {
        "response_text": (
            f"Your case has been escalated to our {state.get('target_team', 'specialist')} team. "
            f"Reason: {state.get('escalation_reason', 'requires specialist attention')}. "
            f"Priority: {state.get('priority', 'P3')}. "
            f"A team member will contact you within 2 hours."
        ),
        "response_confidence": 0.95,
        "references_cited": [],
        "suggested_next_action": "Our specialist team will reach out to you shortly.",
        "approval_status": "n/a",
        "agents_called": ["escalation_handler"],
        "audit_trail": [{
            "agent": "escalation_handler",
            "action": "escalate_to_human",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"team={state.get('target_team')}, priority={state.get('priority')}",
        }],
    }
    try:
        merged: AgentState = {**state, **update}
        save_audit_log(build_audit_entry_from_state(merged))
    except Exception:
        # Audit must never crash the pipeline.
        pass
    return update


def _await_approval(state: AgentState) -> AgentState:
    """Terminal node for HITL approval — parks draft response in the queue.

    The customer sees a holding message; the actual response is queued for a
    reviewer via ``python -m src.governance.approval_queue``.
    """
    record = None
    try:
        record = submit_for_approval(
            session_id=str(state.get("session_id") or ""),
            customer_id=str(state.get("customer_id") or ""),
            intent=str(state.get("intent") or ""),
            risk_score=float(state.get("risk_score") or 0.0),
            target_team=str(state.get("target_team") or ""),
            priority=str(state.get("priority") or "P3"),
            sla_target=str(state.get("sla_target") or ""),
            draft_response=str(state.get("response_text") or ""),
            references_cited=list(state.get("references_cited") or []),
            risk_factors=list(state.get("risk_factors") or []),
        )
    except Exception:
        record = None

    approval_id = record.approval_id if record else ""
    approval_status = record.status if record else "pending"

    holding_text = (
        "Thanks for your patience — your request needs a quick human review. "
        "A specialist will confirm the next steps shortly"
    )
    if record and record.sla_target:
        holding_text += f" (review SLA: {record.sla_target})."
    else:
        holding_text += "."

    update: dict = {
        "response_text": holding_text,
        "response_confidence": 0.75,
        "suggested_next_action": "Wait for specialist confirmation; we will reach out via your preferred channel.",
        "approval_status": approval_status,
        "approval_id": approval_id,
        "agents_called": ["approval_handler"],
        "audit_trail": [{
            "agent": "approval_handler",
            "action": "submit_for_approval",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": (
                f"approval_id={approval_id} status={approval_status} "
                f"team={state.get('target_team')} priority={state.get('priority')}"
            ),
        }],
    }
    try:
        merged: AgentState = {**state, **update}
        save_audit_log(build_audit_entry_from_state(merged))
    except Exception:
        pass
    return update


def _finalize(state: AgentState) -> AgentState:
    """Terminal node for auto-resolved cases — records the audit entry only.

    Lives between ``generate_response`` and ``END`` for the auto-band path so
    the audit log gets a single canonical write per session.
    """
    try:
        save_audit_log(build_audit_entry_from_state(state))
    except Exception:
        pass
    return {
        "approval_status": str(state.get("approval_status") or "auto"),
        "agents_called": ["finalizer"],
        "audit_trail": [{
            "agent": "finalizer",
            "action": "record_audit",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"risk_band={state.get('risk_band', 'auto')}",
        }],
    }


# Wrap all agents with error safety
safe_classify_intent = error_safe("intent_classifier")(classify_intent)
safe_fetch_order = error_safe("order_context")(fetch_order_context)
safe_retrieve_policy = error_safe("policy_retrieval")(retrieve_policy)
safe_advise_product = error_safe("product_advisory")(advise_product)
safe_execute_workflow = error_safe("workflow_automation")(execute_workflow)
safe_check_risk = error_safe("escalation_risk")(check_risk)
safe_generate_response = error_safe("response_generator")(generate_response)
safe_evaluate_quality = error_safe("evaluator")(evaluate_quality)


def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph workflow.

    Flow:
    START -> classify_intent -> [route based on intent/confidence] ->
      -> clarify (if low confidence) -> END
      -> fetch_order -> [route] -> retrieve_policy -> [route] -> execute_workflow
      -> evaluate_quality -> check_risk -> [generate_response | escalate] -> END
    """
    graph = StateGraph(AgentState)

    # Add all nodes (wrapped with error safety)
    graph.add_node("classify_intent", safe_classify_intent)
    graph.add_node("fetch_order", safe_fetch_order)
    graph.add_node("retrieve_policy", safe_retrieve_policy)
    graph.add_node("advise_product", safe_advise_product)
    graph.add_node("execute_workflow", safe_execute_workflow)
    graph.add_node("evaluate", safe_evaluate_quality)
    graph.add_node("check_risk", safe_check_risk)
    graph.add_node("generate_response", safe_generate_response)
    graph.add_node("escalate", _escalate)
    graph.add_node("await_approval", _await_approval)
    graph.add_node("finalize", _finalize)
    graph.add_node("clarify", _clarify)

    # Entry point
    graph.add_edge(START, "classify_intent")

    # After intent classification — conditional routing (now includes "clarify")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {
            "fetch_order": "fetch_order",
            "retrieve_policy": "retrieve_policy",
            "advise_product": "advise_product",
            "direct_response": "evaluate",
            "clarify": "clarify",
        },
    )

    # Clarify is a terminal node — ask and wait for next message
    graph.add_edge("clarify", END)

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

    # After risk check — three outcomes:
    #   escalate         -> hand off, no AI response served
    #   await_approval   -> generate a draft first, then queue for human review
    #   generate_response -> safe to serve directly
    graph.add_conditional_edges(
        "check_risk",
        route_after_risk,
        {
            "generate_response": "generate_response",
            "await_approval": "generate_response",  # still draft first, then route in next edge
            "escalate": "escalate",
        },
    )

    # After response is generated, decide whether to serve it or hold for approval.
    graph.add_conditional_edges(
        "generate_response",
        route_after_response,
        {
            "await_approval": "await_approval",
            "end": "finalize",
        },
    )

    # Terminal nodes — finalize writes the audit log for auto cases; the other
    # two terminals write their own audit entries (escalate/await_approval).
    graph.add_edge("finalize", END)
    graph.add_edge("escalate", END)
    graph.add_edge("await_approval", END)

    return graph


def compile_graph():
    """Build and compile the graph for execution."""
    graph = build_graph()
    return graph.compile()


# Pre-compiled graph instance for import
app = compile_graph()
