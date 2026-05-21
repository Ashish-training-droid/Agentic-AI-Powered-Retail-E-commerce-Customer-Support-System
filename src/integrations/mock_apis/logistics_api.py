"""
Mock Logistics / Shipment API (Person 3).
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import error_response, find_by_id, load_json_file, ok_response


def _resolve_shipment(
    shipment_id: str | None = None, order_id: str | None = None
) -> dict[str, Any] | None:
    shipments = load_json_file("shipments.json")
    if shipment_id:
        record = find_by_id(shipments, "shipment_id", shipment_id.strip())
        if record:
            return record
    if order_id:
        return find_by_id(shipments, "order_id", order_id.strip().upper())
    return None


def get_shipment_tracking(
    shipment_id: str | None = None, order_id: str | None = None
) -> dict[str, Any]:
    """Retrieve shipment tracking details."""
    if not shipment_id and not order_id:
        return error_response("shipment_id or order_id is required")

    shipment = _resolve_shipment(shipment_id, order_id)
    if not shipment:
        ref = shipment_id or order_id
        return error_response(f"Shipment not found for reference: {ref}")

    tracking = shipment.get("tracking_number") or shipment.get("tracking")
    data = {
        "shipment_id": shipment.get("shipment_id"),
        "order_id": shipment.get("order_id"),
        "customer_id": shipment.get("customer_id"),
        "carrier": shipment.get("carrier"),
        "tracking_number": tracking,
        "status": shipment.get("status"),
        "origin_warehouse": shipment.get("origin_warehouse"),
        "destination_city": shipment.get("destination_city"),
        "shipped_on": shipment.get("shipped_on"),
        "delivered_on": shipment.get("delivered_on"),
        "eta": shipment.get("eta"),
        "notes": shipment.get("notes"),
    }
    return ok_response(data)


def get_delivery_eta(
    shipment_id: str | None = None, order_id: str | None = None
) -> dict[str, Any]:
    """Return estimated delivery date and shipment status."""
    if not shipment_id and not order_id:
        return error_response("shipment_id or order_id is required")

    shipment = _resolve_shipment(shipment_id, order_id)
    if not shipment:
        ref = shipment_id or order_id
        return error_response(f"Shipment not found for reference: {ref}")

    status = shipment.get("status")
    eta = shipment.get("eta")
    delivered_on = shipment.get("delivered_on")

    if status == "delivered" and delivered_on:
        message = f"Order was delivered on {delivered_on}."
    elif eta:
        message = f"Estimated delivery: {eta}."
    else:
        message = "ETA not available yet; shipment is being prepared."

    data = {
        "shipment_id": shipment.get("shipment_id"),
        "order_id": shipment.get("order_id"),
        "status": status,
        "eta": eta,
        "delivered_on": delivered_on,
        "carrier": shipment.get("carrier"),
        "message": message,
    }
    return ok_response(data)
