"""
Workflow Automation Agent (Pallavi (Person 3))

Initiates guided self-service workflows via src/integrations/mock_apis/.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from src.integrations.mock_apis.guardrails import requires_approval
from src.integrations.mock_apis.payment_api import get_payment_status, process_refund
from src.integrations.mock_apis.return_api import create_return_request, get_return_status
from src.integrations.mock_apis.ticket_api import create_ticket, update_ticket
from src.orchestrator.state import AgentState


WORKFLOW_MAP: dict[str, str] = {
    "return_request": "initiate_return",
    "refund_status": "check_refund",
    "order_tracking": "send_invoice",
    "delivery_complaint": "update_address",
    "damaged_product": "create_ticket",
    "escalation": "escalate_case",
    "complaint": "escalate_case",
}

SENSITIVE_ACTIONS = frozenset({"initiate_return", "check_refund", "escalate_case"})

_BLOCKED_SHIPMENT_STATUSES = frozenset({"in_transit", "delivered", "lost", "lost_in_transit"})
_HUMAN_REVIEW_AMOUNT_THRESHOLD = 5000


def _api_data(response: dict[str, Any] | None) -> dict[str, Any]:
    if not response or not response.get("success"):
        return {}
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def _api_error(response: dict[str, Any] | None, default: str = "Request failed") -> str:
    if not response:
        return default
    return str(response.get("error") or default)


def _get_amount(order_context: dict[str, Any]) -> int:
    payment = order_context.get("payment") or {}
    amount = payment.get("amount", order_context.get("total_amount", 0))
    try:
        return int(amount or 0)
    except (TypeError, ValueError):
        return 0


def _get_order_id(order_context: dict[str, Any]) -> str:
    return str(order_context.get("order_id") or "").strip().upper()


def _get_customer_id(order_context: dict[str, Any]) -> str:
    customer = order_context.get("customer") or {}
    return str(
        order_context.get("customer_id") or customer.get("customer_id") or ""
    ).strip().upper()


def _get_risk_signals(order_context: dict[str, Any]) -> dict[str, bool]:
    signals = order_context.get("risk_signals")
    if not isinstance(signals, dict):
        return {}
    return {k: bool(v) for k, v in signals.items()}


def _should_escalate(order_context: dict[str, Any]) -> bool:
    """Escalate lost shipments, high-value damage, angry customers, payment failures."""
    signals = _get_risk_signals(order_context)
    if signals.get("lost_shipment"):
        return True
    if signals.get("angry_customer"):
        return True
    if signals.get("payment_failed"):
        return True
    if signals.get("damaged_product") and signals.get("high_value_order"):
        return True
    return False


def _determine_priority(order_context: dict[str, Any]) -> str:
    tier = str(order_context.get("customer_tier") or "").lower()
    signals = _get_risk_signals(order_context)

    if tier == "vip" or any(
        signals.get(flag)
        for flag in ("damaged_product", "lost_shipment", "high_value_order")
    ):
        return "high"
    if signals.get("angry_customer") or signals.get("payment_failed"):
        return "medium"
    return "low"


def _needs_human_review(workflow_action: str, order_context: dict[str, Any]) -> bool:
    amount = _get_amount(order_context)
    if workflow_action == "escalate_case":
        return True
    if workflow_action == "initiate_return":
        needed, _ = requires_approval("initiate_return", amount)
        return needed
    if workflow_action == "check_refund":
        needed, _ = requires_approval("process_refund", amount)
        return needed
    if workflow_action == "create_ticket" and _determine_priority(order_context) == "high":
        return True
    return False


def _workflow_result(
    *,
    success: bool,
    workflow_status: str,
    generated_id: str | None,
    message: str,
    next_step: str,
    requires_human_review: bool,
    **extra: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": success,
        "workflow_status": workflow_status,
        "generated_id": generated_id,
        "message": message,
        "next_step": next_step,
        "requires_human_review": requires_human_review,
    }
    result.update(extra)
    return result


def _missing_order_result() -> dict[str, Any]:
    return _workflow_result(
        success=False,
        workflow_status="missing_order_context",
        generated_id=None,
        message=(
            "I need your order details to proceed. Please share your order ID "
            "(for example, SE10234) or confirm the account this order belongs to."
        ),
        next_step="provide_order_id",
        requires_human_review=False,
    )


def _is_return_allowed(order_context: dict[str, Any]) -> tuple[bool, str]:
    if order_context.get("status") != "delivered":
        return False, "Returns are only available for delivered orders."

    if "return_eligible" in order_context and not order_context.get("return_eligible"):
        return False, "This order is not eligible for return under current policy."

    return True, ""


def _workflow_initiate_return(order_context: dict[str, Any]) -> dict[str, Any]:
    allowed, reason = _is_return_allowed(order_context)
    if not allowed:
        return _workflow_result(
            success=False,
            workflow_status="ineligible",
            generated_id=None,
            message=reason,
            next_step="review_return_policy",
            requires_human_review=False,
        )

    order_id = _get_order_id(order_context)
    amount = _get_amount(order_context)
    needs_review, approver = requires_approval("initiate_return", amount)

    existing_resp = get_return_status(order_id=order_id)
    existing = _api_data(existing_resp)
    if existing and existing.get("status") not in ("completed", "rejected", "cancelled"):
        return_id = str(existing.get("return_id", ""))
        status = str(existing.get("status", "requested"))
        return _workflow_result(
            success=True,
            workflow_status=status,
            generated_id=return_id or None,
            message=existing_resp.get("data", {}).get("message", f"Return {return_id} already active."),
            next_step="track_return",
            requires_human_review=needs_review,
            return_id=return_id,
            pickup_date=existing.get("pickup_date"),
        )

    items = order_context.get("items") or []
    reason_text = "Customer return request"
    returns = order_context.get("returns") or order_context.get("return_history") or []
    if isinstance(returns, list) and returns and returns[0].get("reason"):
        reason_text = str(returns[0].get("reason"))

    api_resp = create_return_request(order_id, reason=reason_text, items=items)
    data = _api_data(api_resp)
    if not data:
        return _workflow_result(
            success=False,
            workflow_status="api_error",
            generated_id=None,
            message=_api_error(api_resp, "Could not create return request."),
            next_step="contact_support",
            requires_human_review=False,
        )

    return_id = str(data.get("return_id", ""))
    api_review = bool(data.get("requires_human_approval")) or needs_review
    status = str(data.get("status", "requested"))
    workflow_status = "pending_review" if api_review else status

    return _workflow_result(
        success=True,
        workflow_status=workflow_status,
        generated_id=return_id or None,
        message=str(data.get("message", f"Return {return_id} created.")),
        next_step="await_human_approval" if api_review else "await_pickup",
        requires_human_review=api_review,
        return_id=return_id,
        approver=approver if api_review else None,
        order_id=order_id,
    )


def _workflow_check_refund(order_context: dict[str, Any]) -> dict[str, Any]:
    order_id = _get_order_id(order_context)
    amount = _get_amount(order_context)
    needs_review, approver = requires_approval("process_refund", amount)

    return_resp = get_return_status(order_id=order_id)
    return_data = _api_data(return_resp)

    payment_resp = get_payment_status(order_id=order_id)
    payment_data = _api_data(payment_resp)

    refund_status = str(order_context.get("refund_status") or "none").lower()
    refunds = order_context.get("refunds") or []
    generated_id = None
    expected_by = None

    if isinstance(refunds, list) and refunds:
        latest = refunds[-1]
        generated_id = latest.get("refund_id")
        refund_status = str(latest.get("status") or refund_status).lower()
        expected_by = latest.get("expected_completion") or latest.get("completed_on")

    if refund_status == "none" and not refunds and not return_data:
        return _workflow_result(
            success=True,
            workflow_status="not_initiated",
            generated_id=None,
            message="No refund has been initiated for this order yet.",
            next_step="initiate_return_if_needed",
            requires_human_review=False,
            refund_status="not_initiated",
            amount=amount,
            payment_status=payment_data.get("status"),
        )

    return_status = str(return_data.get("status", "")).lower() if return_data else ""
    if (
        refund_status in ("none", "not_initiated")
        and return_status in ("received_at_warehouse", "picked_up", "completed")
    ):
        refund_api = process_refund(
            order_id,
            amount=float(amount),
            reason=return_data.get("reason", "Return processed"),
        )
        refund_api_data = _api_data(refund_api)
        if refund_api_data:
            generated_id = refund_api_data.get("refund_id")
            refund_status = str(refund_api_data.get("status", "processing")).lower()
            expected_by = refund_api_data.get("expected_completion")
            needs_review = bool(refund_api_data.get("requires_human_approval")) or needs_review
            message = str(refund_api_data.get("message", "Refund initiated."))
            return _workflow_result(
                success=True,
                workflow_status=refund_status,
                generated_id=generated_id,
                message=message,
                next_step="await_human_approval" if needs_review else "await_refund_completion",
                requires_human_review=needs_review,
                refund_status=refund_status,
                expected_by=expected_by,
                amount=amount,
                approver=refund_api_data.get("approver") if needs_review else None,
            )

    if refund_status in ("processing", "pending", "pending_approval", "approved_awaiting_transfer"):
        message = (
            f"Your refund of Rs {amount:,} is {refund_status}. "
            f"Expected completion: {expected_by or 'within 5-7 business days'}."
        )
        next_step = "await_human_approval" if needs_review else "await_refund_completion"
        workflow_status = refund_status
    elif refund_status == "completed":
        message = f"Your refund of Rs {amount:,} has been completed."
        next_step = "none"
        workflow_status = "completed"
    else:
        pay_status = payment_data.get("status", "unknown")
        message = (
            f"Refund status: {refund_status or 'pending'}. Payment status: {pay_status}."
        )
        next_step = "contact_support"
        workflow_status = refund_status or "unknown"

    return _workflow_result(
        success=True,
        workflow_status=workflow_status,
        generated_id=generated_id,
        message=message,
        next_step=next_step,
        requires_human_review=needs_review,
        refund_status=refund_status,
        expected_by=expected_by,
        amount=amount,
        payment_status=payment_data.get("status"),
        return_status=return_status or None,
        approver=approver if needs_review else None,
    )


def _workflow_send_invoice(order_context: dict[str, Any]) -> dict[str, Any]:
    order_id = _get_order_id(order_context)
    invoice_url = f"https://shopease.com/invoice/{order_id}"

    if "invoice_available" in order_context and not order_context.get("invoice_available"):
        return _workflow_result(
            success=False,
            workflow_status="unavailable",
            generated_id=None,
            message=(
                "Invoice is not yet available for this order. "
                "It can be generated after payment is confirmed."
            ),
            next_step="retry_after_payment",
            requires_human_review=False,
            invoice_url=invoice_url,
        )

    return _workflow_result(
        success=True,
        workflow_status="generated",
        generated_id=order_id,
        message="Your tax invoice link has been generated.",
        next_step="download_invoice",
        requires_human_review=False,
        invoice_url=invoice_url,
    )


def _workflow_create_ticket(
    order_context: dict[str, Any],
    issue_type: str = "damaged_product",
    description: str = "",
) -> dict[str, Any]:
    order_id = _get_order_id(order_context)
    customer_id = _get_customer_id(order_context)
    priority = _determine_priority(order_context)

    if not customer_id:
        return _workflow_result(
            success=False,
            workflow_status="missing_customer",
            generated_id=None,
            message="Customer ID is required to create a support ticket.",
            next_step="provide_customer_id",
            requires_human_review=False,
        )

    if not description:
        notes = order_context.get("crm_notes") or []
        description = notes[0] if notes else f"Support request for order {order_id}"

    api_resp = create_ticket(
        customer_id=customer_id,
        order_id=order_id,
        issue_type=issue_type,
        priority=priority,
        description=description,
    )
    data = _api_data(api_resp)
    if not data:
        return _workflow_result(
            success=False,
            workflow_status="api_error",
            generated_id=None,
            message=_api_error(api_resp, "Could not create support ticket."),
            next_step="contact_support",
            requires_human_review=False,
        )

    ticket_id = str(data.get("ticket_id", ""))
    review = _needs_human_review("create_ticket", order_context)

    if priority == "high" and ticket_id:
        update_ticket(
            ticket_id,
            "in_progress",
            note="High-priority case — assigned to specialist queue.",
        )

    team = "escalation_queue" if priority == "high" else "support_queue"
    return _workflow_result(
        success=True,
        workflow_status=str(data.get("status", "open")),
        generated_id=ticket_id or None,
        message=str(data.get("message", f"Ticket {ticket_id} created.")),
        next_step="await_agent_callback" if priority == "high" else "track_ticket",
        requires_human_review=review,
        ticket_id=ticket_id,
        priority=priority,
        assigned_team=team,
    )


def _workflow_update_address(order_context: dict[str, Any]) -> dict[str, Any]:
    shipment = order_context.get("shipment") or {}
    ship_status = str(shipment.get("status") or "").lower()

    if ship_status in _BLOCKED_SHIPMENT_STATUSES:
        return _workflow_result(
            success=False,
            workflow_status="blocked",
            generated_id=None,
            message=(
                "Shipping address cannot be updated because the shipment is already "
                f"{ship_status.replace('_', ' ')}."
            ),
            next_step="contact_courier_or_support",
            requires_human_review=False,
            shipment_status=ship_status,
        )

    order_id = _get_order_id(order_context)
    return _workflow_result(
        success=True,
        workflow_status="updated",
        generated_id=order_id,
        message="Shipping address update request accepted. Changes apply before dispatch.",
        next_step="confirm_address_with_customer",
        requires_human_review=False,
        shipment_status=ship_status or "pending_dispatch",
    )


def _workflow_escalate_case(order_context: dict[str, Any]) -> dict[str, Any]:
    signals = _get_risk_signals(order_context)
    active_flags = [
        flag
        for flag, active in (
            ("lost_shipment", signals.get("lost_shipment")),
            ("high_value_damaged", signals.get("damaged_product") and signals.get("high_value_order")),
            ("damaged_product", signals.get("damaged_product")),
            ("angry_customer", signals.get("angry_customer")),
            ("payment_failed", signals.get("payment_failed")),
        )
        if active
    ]

    if not _should_escalate(order_context):
        return _workflow_result(
            success=False,
            workflow_status="not_required",
            generated_id=None,
            message="This case does not meet automatic escalation criteria.",
            next_step="continue_standard_support",
            requires_human_review=False,
            risk_signals=signals,
        )

    order_id = _get_order_id(order_context)
    customer_id = _get_customer_id(order_context)
    priority = "high"
    escalation_reason = ", ".join(active_flags)
    description = (
        f"Escalated case for order {order_id}: {escalation_reason}. "
        f"{' '.join(order_context.get('crm_notes') or [])[:200]}"
    ).strip()

    create_resp = create_ticket(
        customer_id=customer_id,
        order_id=order_id,
        issue_type="escalation",
        priority=priority,
        description=description,
    )
    data = _api_data(create_resp)
    if not data:
        return _workflow_result(
            success=False,
            workflow_status="api_error",
            generated_id=None,
            message=_api_error(create_resp, "Could not escalate case."),
            next_step="contact_support",
            requires_human_review=True,
            risk_signals=signals,
        )

    ticket_id = str(data.get("ticket_id", ""))
    if ticket_id:
        update_ticket(
            ticket_id,
            "escalated",
            note=f"Auto-escalated: {escalation_reason}",
        )

    team = "escalation_queue"
    return _workflow_result(
        success=True,
        workflow_status="escalated",
        generated_id=ticket_id or None,
        message=(
            f"Case escalated to {team} due to: {escalation_reason}. "
            f"Reference ticket {ticket_id}."
        ),
        next_step="specialist_follow_up",
        requires_human_review=True,
        ticket_id=ticket_id,
        priority=priority,
        target_team=team,
        escalation_reason=escalation_reason,
        risk_signals=signals,
    )


WORKFLOW_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "initiate_return": _workflow_initiate_return,
    "check_refund": _workflow_check_refund,
    "send_invoice": _workflow_send_invoice,
    "create_ticket": lambda ctx: _workflow_create_ticket(ctx, issue_type="damaged_product"),
    "update_address": _workflow_update_address,
    "escalate_case": _workflow_escalate_case,
}

_AUTO_ESCALATE_OVERRIDE_INTENTS = frozenset({
    "damaged_product",
    "delivery_complaint",
    "complaint",
    "escalation",
})


def _resolve_workflow_action(intent: str, order_context: dict[str, Any]) -> str:
    workflow_action = WORKFLOW_MAP.get(intent, "create_ticket")
    if (
        _should_escalate(order_context)
        and workflow_action not in ("initiate_return", "check_refund")
        and (
            workflow_action == "create_ticket"
            or intent in _AUTO_ESCALATE_OVERRIDE_INTENTS
            or WORKFLOW_MAP.get(intent) == "escalate_case"
        )
    ):
        return "escalate_case"
    return workflow_action


def execute_workflow(state: AgentState) -> AgentState:
    """
    LangGraph node: executes the appropriate workflow action.

    Reads: intent, order_context, policy_snippets
    Writes: action_taken, action_result, requires_human_approval, agents_called, audit_trail
    """
    intent = state.get("intent", "")
    order_context = state.get("order_context") or {}

    if not order_context or not _get_order_id(order_context):
        action_result = _missing_order_result()
        return {
            "action_taken": "none",
            "action_result": action_result,
            "requires_human_approval": False,
            "agents_called": ["workflow_automation"],
            "audit_trail": [{
                "agent": "workflow_automation",
                "action": "none",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": "missing_order_context",
            }],
        }

    try:
        workflow_action = _resolve_workflow_action(intent, order_context)
        handler = WORKFLOW_HANDLERS.get(workflow_action, _workflow_create_ticket)
        action_result = handler(order_context)
    except Exception:
        action_result = _workflow_result(
            success=False,
            workflow_status="error",
            generated_id=None,
            message="Workflow could not be completed. Please try again or contact support.",
            next_step="contact_support",
            requires_human_review=False,
        )
        workflow_action = "error"

    if action_result.get("success") and not action_result.get("requires_human_review"):
        action_result["requires_human_review"] = _needs_human_review(
            workflow_action, order_context
        )
    elif not action_result.get("success"):
        action_result["requires_human_review"] = False

    requires_approval = bool(
        action_result.get("success")
        and (
            action_result.get("requires_human_review")
            or (
                workflow_action in SENSITIVE_ACTIONS
                and _get_amount(order_context) > _HUMAN_REVIEW_AMOUNT_THRESHOLD
            )
        )
    )

    return {
        "action_taken": workflow_action,
        "action_result": action_result,
        "requires_human_approval": requires_approval,
        "agents_called": ["workflow_automation"],
        "audit_trail": [{
            "agent": "workflow_automation",
            "action": workflow_action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": (
                f"intent={intent}, success={action_result.get('success')}, "
                f"status={action_result.get('workflow_status')}, "
                f"requires_approval={requires_approval}"
            ),
        }],
    }
