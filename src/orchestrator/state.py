"""
Shared orchestration state for the LangGraph workflow.

This TypedDict defines ALL fields that flow between agents. Each agent reads
what it needs and writes its outputs back. The orchestrator manages the full
state lifecycle.
"""

from __future__ import annotations
from typing import TypedDict, Annotated
from operator import add


class AuditEntry(TypedDict, total=False):
    agent: str
    action: str
    timestamp: str
    details: str


class PolicySnippet(TypedDict, total=False):
    rule: str
    explanation: str
    reference_id: str
    confidence: float


class AgentState(TypedDict, total=False):
    # --- Input (set at start) ---
    session_id: str
    customer_id: str
    channel: str
    message: str
    conversation_history: list[dict]

    # --- Intent Classification output ---
    intent: str
    sub_intent: str
    sentiment: str
    urgency: str
    intent_confidence: float

    # --- Order Context output ---
    order_context: dict
    order_id: str
    customer_tier: str

    # --- Policy Retrieval output ---
    policy_snippets: list[PolicySnippet]
    policy_applies: bool

    # --- Product Advisory output ---
    product_context: dict

    # --- Workflow Automation output ---
    action_taken: str
    action_result: dict
    requires_human_approval: bool

    # --- Escalation & Risk output ---
    risk_score: float
    escalation_required: bool
    escalation_reason: str
    target_team: str
    priority: str

    # --- Response Generation output ---
    response_text: str
    response_confidence: float
    references_cited: list[str]
    suggested_next_action: str

    # --- Evaluator output ---
    quality_score: float
    quality_issues: list[str]

    # --- Governance / Audit ---
    agents_called: Annotated[list[str], add]
    audit_trail: Annotated[list[dict], add]
