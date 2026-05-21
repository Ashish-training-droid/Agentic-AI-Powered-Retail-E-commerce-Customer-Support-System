"""
Mock Order Management API (Person 3).
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import (
    error_response,
    find_by_id,
    load_json_file,
    ok_response,
)


def _load_order(order_id: str) -> dict[str, Any] | None:
    if not order_id:
        return None
    orders = load_json_file("orders.json")
    return find_by_id(orders, "order_id", order_id.strip().upper())


def _payment_for_order(order: dict[str, Any]) -> dict[str, Any] | None:
    payments = load_json_file("payments.json")
    payment_id = order.get("payment_id")
    if payment_id:
        record = find_by_id(payments, "payment_id", payment_id)
        if record:
            return record
    return find_by_id(payments, "order_id", order.get("order_id"))


def _shipment_for_order(order: dict[str, Any]) -> dict[str, Any] | None:
    shipments = load_json_file("shipments.json")
    shipment_id = order.get("shipment_id")
    if shipment_id:
        record = find_by_id(shipments, "shipment_id", shipment_id)
        if record:
            return record
    return find_by_id(shipments, "order_id", order.get("order_id"))


def get_order_status(order_id: str) -> dict[str, Any]:
    """
    Retrieve current order status and linked payment/shipment summary.
    """
    order_id = (order_id or "").strip().upper()
    if not order_id:
        return error_response("order_id is required")

    order = _load_order(order_id)
    if not order:
        return error_response(f"Order {order_id} not found")

    payment = _payment_for_order(order) or {}
    shipment = _shipment_for_order(order) or {}

    data = {
        "order_id": order.get("order_id"),
        "customer_id": order.get("customer_id"),
        "status": order.get("status"),
        "placed_on": order.get("placed_on"),
        "total_amount": order.get("total_amount"),
        "currency": order.get("currency", "INR"),
        "items_count": len(order.get("items") or []),
        "payment_status": payment.get("status"),
        "shipment_status": shipment.get("status"),
        "eta": shipment.get("eta"),
        "tracking_number": shipment.get("tracking_number"),
    }
    return ok_response(data)


def get_order_details(order_id: str) -> dict[str, Any]:
    """Retrieve full order record including line items and references."""
    order_id = (order_id or "").strip().upper()
    if not order_id:
        return error_response("order_id is required")

    order = _load_order(order_id)
    if not order:
        return error_response(f"Order {order_id} not found")

    return ok_response(dict(order))
