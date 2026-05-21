"""
Mock Returns API (Person 3).

Return requests created in-session are stored in memory; existing returns load from returns.json.
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import (
    error_response,
    find_all_by_id,
    find_by_id,
    load_json_file,
    ok_response,
    utc_timestamp,
)
from src.integrations.mock_apis.guardrails import requires_approval

_session_returns: dict[str, dict[str, Any]] = {}

_CANCELLABLE_STATUSES = frozenset({
    "requested", "approved", "pickup_scheduled",
})


def _return_id_for_order(order_id: str) -> str:
    suffix = order_id.replace("SE", "") if order_id.startswith("SE") else order_id
    return f"RET_{suffix}"


def _find_return(
    order_id: str | None = None, return_id: str | None = None
) -> dict[str, Any] | None:
    if return_id:
        rid = return_id.strip()
        if rid in _session_returns:
            return dict(_session_returns[rid])
        record = find_by_id(load_json_file("returns.json"), "return_id", rid)
        if record:
            return dict(record)

    if order_id:
        oid = order_id.strip().upper()
        for record in _session_returns.values():
            if record.get("order_id") == oid:
                return dict(record)
        returns = find_all_by_id(load_json_file("returns.json"), "order_id", oid)
        if returns:
            return dict(returns[-1])
    return None


def create_return_request(
    order_id: str, reason: str = "", items: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Create a return request for a delivered order."""
    order_id = (order_id or "").strip().upper()
    if not order_id:
        return error_response("order_id is required")

    order = find_by_id(load_json_file("orders.json"), "order_id", order_id)
    if not order:
        return error_response(f"Order {order_id} not found")

    if order.get("status") != "delivered":
        return error_response("Returns can only be created for delivered orders.")

    existing = _find_return(order_id=order_id)
    if existing and existing.get("status") not in ("completed", "rejected", "cancelled"):
        return ok_response({
            "return_id": existing.get("return_id"),
            "order_id": order_id,
            "status": existing.get("status"),
            "message": "An active return request already exists for this order.",
            "existing": True,
        })

    line_items = items if items else (order.get("items") or [])
    if not line_items:
        return error_response("No items available to return for this order.")

    first_item = line_items[0] if isinstance(line_items[0], dict) else {}
    amount = int(order.get("total_amount") or 0)
    needs_approval, approver = requires_approval("initiate_return", amount)

    return_id = _return_id_for_order(order_id)
    return_record = {
        "return_id": return_id,
        "order_id": order_id,
        "customer_id": order.get("customer_id"),
        "product_id": first_item.get("product_id"),
        "item_id": first_item.get("item_id"),
        "quantity": first_item.get("quantity", 1),
        "reason": reason or "Customer return request",
        "status": "pending_approval" if needs_approval else "requested",
        "requested_on": utc_timestamp()[:10],
        "refund_eligible": True,
        "pickup_address": order.get("shipping_address"),
        "requires_human_approval": needs_approval,
        "approver": approver if needs_approval else None,
    }
    _session_returns[return_id] = return_record

    message = (
        f"Return {return_id} created and pending {approver} approval."
        if needs_approval
        else f"Return {return_id} created. Pickup will be scheduled shortly."
    )

    return ok_response({
        "return_id": return_id,
        "order_id": order_id,
        "status": return_record["status"],
        "reason": return_record["reason"],
        "requires_human_approval": needs_approval,
        "message": message,
    })


def get_return_status(
    order_id: str | None = None, return_id: str | None = None
) -> dict[str, Any]:
    """Get return status by return_id or order_id."""
    if not order_id and not return_id:
        return error_response("order_id or return_id is required")

    record = _find_return(
        order_id=order_id.strip().upper() if order_id else None,
        return_id=return_id,
    )
    if not record:
        ref = return_id or order_id
        return error_response(f"Return not found for reference: {ref}")

    return ok_response({
        "return_id": record.get("return_id"),
        "order_id": record.get("order_id"),
        "customer_id": record.get("customer_id"),
        "product_id": record.get("product_id"),
        "status": record.get("status"),
        "reason": record.get("reason"),
        "requested_on": record.get("requested_on"),
        "pickup_date": record.get("pickup_date"),
        "refund_eligible": record.get("refund_eligible", True),
    })


def cancel_return(return_id: str) -> dict[str, Any]:
    """Cancel an open return request."""
    return_id = (return_id or "").strip()
    if not return_id:
        return error_response("return_id is required")

    record = _find_return(return_id=return_id)
    if not record:
        return error_response(f"Return {return_id} not found")

    status = str(record.get("status", "")).lower()
    if status in ("completed", "cancelled", "picked_up", "received_at_warehouse"):
        return error_response(f"Return {return_id} cannot be cancelled in status '{status}'.")

    if status not in _CANCELLABLE_STATUSES and return_id not in _session_returns:
        return error_response(f"Return {return_id} cannot be cancelled in status '{status}'.")

    record["status"] = "cancelled"
    record["cancelled_on"] = utc_timestamp()[:10]
    _session_returns[return_id] = record

    return ok_response({
        "return_id": return_id,
        "order_id": record.get("order_id"),
        "status": "cancelled",
        "message": f"Return {return_id} has been cancelled.",
    })
