"""
Action guardrails for sensitive mock API operations (Person 3).
"""

from __future__ import annotations

from typing import Any

SENSITIVE_ACTIONS: dict[str, dict[str, Any]] = {
    "process_refund": {"threshold": 5000, "approval": "finance"},
    "initiate_return": {"threshold": 5000, "approval": "senior_agent"},
    "cancel_order": {"threshold": 0, "approval": "senior_agent"},
    "override_policy": {"threshold": 0, "approval": "manager"},
    "escalate_case": {"threshold": 0, "approval": "escalation_queue"},
}


def requires_approval(action: str, amount: float = 0) -> tuple[bool, str]:
    """
    Check if an action needs human approval before execution.

    Returns:
        (needs_approval, approver_role)
    """
    config = SENSITIVE_ACTIONS.get(action)
    if not config:
        return False, ""

    threshold = float(config.get("threshold", 0))
    approver = str(config.get("approval", "manager"))

    if threshold <= 0:
        return True, approver
    if amount > threshold:
        return True, approver
    return False, ""
