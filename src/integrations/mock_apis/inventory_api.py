"""
Mock Inventory API (Person 3).
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import error_response, find_by_id, load_json_file, ok_response


def _load_inventory(product_id: str) -> dict[str, Any] | None:
    product_id = (product_id or "").strip().upper()
    if not product_id:
        return None
    return find_by_id(load_json_file("inventory.json"), "product_id", product_id)


def check_inventory(product_id: str) -> dict[str, Any]:
    """Check whether a product is in stock and available to ship."""
    product_id = (product_id or "").strip().upper()
    if not product_id:
        return error_response("product_id is required")

    record = _load_inventory(product_id)
    if not record:
        return error_response(f"Inventory record not found for product {product_id}")

    available = int(record.get("quantity_available") or 0)
    in_stock = available > 0

    data = {
        "product_id": product_id,
        "name": record.get("name"),
        "in_stock": in_stock,
        "quantity_available": available,
        "quantity_reserved": record.get("quantity_reserved", 0),
        "warehouse": record.get("warehouse"),
        "reorder_level": record.get("reorder_level"),
        "unit_price_inr": record.get("unit_price_inr"),
    }
    return ok_response(data)


def get_stock_level(product_id: str) -> dict[str, Any]:
    """Return detailed stock levels for a product."""
    product_id = (product_id or "").strip().upper()
    if not product_id:
        return error_response("product_id is required")

    record = _load_inventory(product_id)
    if not record:
        return error_response(f"Inventory record not found for product {product_id}")

    available = int(record.get("quantity_available") or 0)
    reserved = int(record.get("quantity_reserved") or 0)
    incoming = int(record.get("quantity_incoming") or 0)

    data = {
        "product_id": product_id,
        "sku": record.get("sku", product_id),
        "name": record.get("name"),
        "category": record.get("category"),
        "warehouse": record.get("warehouse"),
        "quantity_available": available,
        "quantity_reserved": reserved,
        "quantity_incoming": incoming,
        "total_on_hand": available + reserved,
        "last_restocked": record.get("last_restocked"),
        "stock_status": "in_stock" if available > 0 else "out_of_stock",
    }
    return ok_response(data)
