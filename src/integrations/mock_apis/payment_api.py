"""
Mock Payment API (Person 3).
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import (
    error_response,
    find_by_id,
    load_json_file,
    ok_response,
    utc_timestamp,
)
from src.integrations.mock_apis.guardrails import requires_approval


def _resolve_payment(
    payment_id: str | None = None, order_id: str | None = None
) -> dict[str, Any] | None:
    payments = load_json_file("payments.json")
    if payment_id:
        record = find_by_id(payments, "payment_id", payment_id.strip())
        if record:
            return record
    if order_id:
        return find_by_id(payments, "order_id", order_id.strip().upper())
    return None


def get_payment_status(
    payment_id: str | None = None, order_id: str | None = None
) -> dict[str, Any]:
    """Retrieve payment status by payment_id or order_id."""
    if not payment_id and not order_id:
        return error_response("payment_id or order_id is required")

    payment = _resolve_payment(payment_id, order_id)
    if not payment:
        ref = payment_id or order_id
        return error_response(f"Payment not found for reference: {ref}")

    data = {
        "payment_id": payment.get("payment_id"),
        "order_id": payment.get("order_id"),
        "customer_id": payment.get("customer_id"),
        "status": payment.get("status"),
        "method": payment.get("method"),
        "amount": payment.get("amount"),
        "currency": payment.get("currency", "INR"),
        "transaction_ref": payment.get("transaction_ref"),
        "paid_on": payment.get("paid_on"),
        "gateway": payment.get("gateway"),
        "failure_reason": payment.get("failure_reason"),
    }
    return ok_response(data)


def process_refund(
    order_id: str, amount: float | None = None, reason: str = ""
) -> dict[str, Any]:
    """
    Initiate a refund for an order. High-value refunds require human approval.
    """
    order_id = (order_id or "").strip().upper()
    if not order_id:
        return error_response("order_id is required")

    payment = _resolve_payment(order_id=order_id)
    if not payment:
        return error_response(f"No payment record found for order {order_id}")

    refund_amount = float(amount if amount is not None else payment.get("amount") or 0)
    needs_approval, approver = requires_approval("process_refund", refund_amount)

    suffix = order_id.replace("SE", "")
    refund_id = f"REF_{suffix}"

    existing = find_by_id(load_json_file("refunds.json"), "order_id", order_id)
    if existing:
        refund_id = str(existing.get("refund_id", refund_id))

    data: dict[str, Any] = {
        "refund_id": refund_id,
        "order_id": order_id,
        "payment_id": payment.get("payment_id"),
        "amount": refund_amount,
        "currency": payment.get("currency", "INR"),
        "method": payment.get("method"),
        "reason": reason or "Customer refund request",
        "status": "pending_approval" if needs_approval else "processing",
        "initiated_on": utc_timestamp()[:10],
        "requires_human_approval": needs_approval,
        "approver": approver if needs_approval else None,
        "expected_completion": "2026-05-25",
    }

    if needs_approval:
        data["message"] = (
            f"Refund of Rs {refund_amount:,.0f} queued for {approver} approval."
        )
    else:
        data["message"] = f"Refund {refund_id} is being processed."

    return ok_response(data)
