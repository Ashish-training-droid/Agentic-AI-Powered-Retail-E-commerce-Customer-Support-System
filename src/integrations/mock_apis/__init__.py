"""
Mock API integrations for ShopEase (Person 3).

Loads backend records from data/mock/ JSON files and exposes tool-style functions
for orders, payments, logistics, inventory, CRM, tickets, and returns.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_DATA_DIR = _REPO_ROOT / "data" / "mock"

FILE_RECORD_KEYS: dict[str, str] = {
    "customers.json": "customers",
    "orders.json": "orders",
    "payments.json": "payments",
    "shipments.json": "shipments",
    "refunds.json": "refunds",
    "returns.json": "returns",
    "crm_history.json": "crm_history",
    "inventory.json": "inventory",
}

_json_cache: dict[str, list[dict[str, Any]]] = {}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def ok_response(data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "timestamp": utc_timestamp(), "data": data}


def error_response(message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "timestamp": utc_timestamp(),
        "error": message,
    }
    payload.update(extra)
    return payload


def load_json_file(filename: str) -> list[dict[str, Any]]:
    """Load records from a mock JSON file. Returns [] if missing or invalid."""
    if filename in _json_cache:
        return _json_cache[filename]

    path = MOCK_DATA_DIR / filename
    if not path.is_file():
        _json_cache[filename] = []
        return []

    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        _json_cache[filename] = []
        return []

    record_key = FILE_RECORD_KEYS.get(filename)
    if not record_key:
        _json_cache[filename] = []
        return []

    records = payload.get(record_key, [])
    if not isinstance(records, list):
        records = []

    _json_cache[filename] = [r for r in records if isinstance(r, dict)]
    return _json_cache[filename]


def find_by_id(
    records: list[dict[str, Any]], key: str, value: Any
) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    for record in records:
        if record.get(key) == value:
            return record
    return None


def find_all_by_id(
    records: list[dict[str, Any]], key: str, value: Any
) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    return [r for r in records if r.get(key) == value]


def clear_cache() -> None:
    """Clear in-memory JSON cache (useful for tests)."""
    _json_cache.clear()


__all__ = [
    "MOCK_DATA_DIR",
    "load_json_file",
    "find_by_id",
    "find_all_by_id",
    "ok_response",
    "error_response",
    "utc_timestamp",
    "clear_cache",
    "get_order_status",
    "get_order_details",
    "get_payment_status",
    "process_refund",
    "get_shipment_tracking",
    "get_delivery_eta",
    "check_inventory",
    "get_stock_level",
    "get_crm_history",
    "get_customer_profile",
    "create_ticket",
    "get_ticket_status",
    "update_ticket",
    "create_return_request",
    "get_return_status",
    "cancel_return",
    "requires_approval",
    "SENSITIVE_ACTIONS",
]


def __getattr__(name: str):
    """Lazy exports to avoid circular imports between API modules."""
    if name == "requires_approval":
        from src.integrations.mock_apis.guardrails import requires_approval
        return requires_approval
    if name == "SENSITIVE_ACTIONS":
        from src.integrations.mock_apis.guardrails import SENSITIVE_ACTIONS
        return SENSITIVE_ACTIONS
    if name in ("get_order_status", "get_order_details"):
        from src.integrations.mock_apis import order_api
        return getattr(order_api, name)
    if name in ("get_payment_status", "process_refund"):
        from src.integrations.mock_apis import payment_api
        return getattr(payment_api, name)
    if name in ("get_shipment_tracking", "get_delivery_eta"):
        from src.integrations.mock_apis import logistics_api
        return getattr(logistics_api, name)
    if name in ("check_inventory", "get_stock_level"):
        from src.integrations.mock_apis import inventory_api
        return getattr(inventory_api, name)
    if name in ("get_crm_history", "get_customer_profile"):
        from src.integrations.mock_apis import crm_api
        return getattr(crm_api, name)
    if name in ("create_ticket", "get_ticket_status", "update_ticket"):
        from src.integrations.mock_apis import ticket_api
        return getattr(ticket_api, name)
    if name in ("create_return_request", "get_return_status", "cancel_return"):
        from src.integrations.mock_apis import return_api
        return getattr(return_api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
