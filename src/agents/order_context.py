"""
Order Context Agent (Pallavi (Person 3))

Retrieves unified order, shipment, payment, invoice, return, and CRM history
for a given customer/order from data/mock/ JSON files.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.orchestrator.state import AgentState

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOCK_DATA_DIR = _REPO_ROOT / "data" / "mock"

_FILE_RECORD_KEYS: dict[str, str] = {
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

_HIGH_VALUE_THRESHOLD = 100_000
_LOST_SHIPMENT_STATUSES = frozenset({"lost", "lost_in_transit"})
_DAMAGED_KEYWORDS = (
    "damaged", "damage", "broken", "cracked", "defective", "defect",
)
_ANGRY_KEYWORDS = ("angry", "frustrated", "furious", "extremely frustrated", "upset")
_INVOICE_ELIGIBLE_ORDER_STATUSES = frozenset(
    {"shipped", "delivered", "returned", "refund_initiated"}
)


def load_json_file(filename: str) -> list[dict[str, Any]]:
    """Load records from a mock data JSON file. Returns [] if missing or invalid."""
    if filename in _json_cache:
        return _json_cache[filename]

    path = _MOCK_DATA_DIR / filename
    if not path.is_file():
        _json_cache[filename] = []
        return []

    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        _json_cache[filename] = []
        return []

    record_key = _FILE_RECORD_KEYS.get(filename)
    if not record_key:
        _json_cache[filename] = []
        return []

    records = payload.get(record_key, [])
    if not isinstance(records, list):
        records = []

    normalized = [r for r in records if isinstance(r, dict)]
    _json_cache[filename] = normalized
    return normalized


def find_by_id(
    records: list[dict[str, Any]], key: str, value: Any
) -> dict[str, Any] | None:
    """Return the first record whose key matches value, or None."""
    if value is None or value == "":
        return None
    for record in records:
        if record.get(key) == value:
            return record
    return None


def find_all_by_id(
    records: list[dict[str, Any]], key: str, value: Any
) -> list[dict[str, Any]]:
    """Return all records whose key matches value."""
    if value is None or value == "":
        return []
    return [r for r in records if r.get(key) == value]


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _normalize_tier(tier: str | None) -> str:
    """Map customer tier to values expected by downstream agents."""
    if not tier:
        return "regular"
    tier_lower = tier.lower()
    if tier_lower == "standard":
        return "regular"
    return tier_lower


def _normalize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shape order line items for legacy consumers (sku/qty/price) and new fields."""
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        product_id = item.get("product_id") or item.get("sku", "")
        quantity = item.get("quantity", item.get("qty", 1))
        unit_price = item.get("unit_price", item.get("price", 0))
        normalized.append({
            "item_id": item.get("item_id"),
            "product_id": product_id,
            "name": item.get("name", ""),
            "sku": product_id,
            "qty": quantity,
            "quantity": quantity,
            "price": unit_price,
            "unit_price": unit_price,
            "line_total": item.get("line_total", unit_price * quantity),
            "category": item.get("category"),
            "subcategory": item.get("subcategory"),
        })
    return normalized


def _normalize_payment(payment: dict[str, Any] | None, order: dict[str, Any]) -> dict[str, Any]:
    if not payment:
        return {
            "method": None,
            "status": "unknown",
            "amount": order.get("total_amount", 0),
            "currency": order.get("currency", "INR"),
        }
    return {
        "payment_id": payment.get("payment_id"),
        "method": payment.get("method"),
        "status": payment.get("status"),
        "amount": payment.get("amount", order.get("total_amount", 0)),
        "currency": payment.get("currency", order.get("currency", "INR")),
        "transaction_ref": payment.get("transaction_ref"),
        "paid_on": payment.get("paid_on"),
        "gateway": payment.get("gateway"),
        "failure_reason": payment.get("failure_reason"),
    }


def _normalize_shipment(shipment: dict[str, Any] | None) -> dict[str, Any]:
    if not shipment:
        return {
            "carrier": None,
            "tracking": None,
            "tracking_number": None,
            "status": "unknown",
            "eta": None,
        }
    tracking = shipment.get("tracking_number") or shipment.get("tracking")
    return {
        "shipment_id": shipment.get("shipment_id"),
        "carrier": shipment.get("carrier"),
        "tracking": tracking,
        "tracking_number": tracking,
        "status": shipment.get("status"),
        "eta": shipment.get("eta"),
        "shipped_on": shipment.get("shipped_on"),
        "delivered_on": shipment.get("delivered_on"),
        "origin_warehouse": shipment.get("origin_warehouse"),
        "destination_city": shipment.get("destination_city"),
        "notes": shipment.get("notes"),
    }


def _crm_notes_for_context(crm_records: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    for ticket in crm_records:
        summary = ticket.get("message_summary") or ticket.get("subject") or ""
        if not summary:
            continue
        created = ticket.get("created_on", "")
        intent = ticket.get("intent", "")
        prefix = f"{created}: " if created else ""
        suffix = f" ({intent})" if intent else ""
        notes.append(f"{prefix}{summary}{suffix}".strip())
    return notes


def _infer_crm_sentiment(crm_records: list[dict[str, Any]]) -> str:
    for ticket in crm_records:
        for field in ("sentiment",):
            sentiment = str(ticket.get(field) or "").lower()
            if sentiment in ("angry", "frustrated", "negative"):
                return sentiment
        text = " ".join(
            str(ticket.get(k) or "")
            for k in ("message_summary", "subject", "intent")
        ).lower()
        if any(word in text for word in _ANGRY_KEYWORDS):
            return "frustrated"
        if "damaged_product" in text or ticket.get("intent") == "damaged_product":
            return "frustrated"
    return "neutral"


def _text_mentions_damaged(*texts: str | None) -> bool:
    combined = " ".join(t for t in texts if t).lower()
    return any(keyword in combined for keyword in _DAMAGED_KEYWORDS)


def _compute_return_eligible(
    order: dict[str, Any],
    returns: list[dict[str, Any]],
) -> bool:
    if order.get("status") != "delivered":
        return False
    if order.get("demo_scenario") == "return_eligible":
        return True
    active_return = any(
        r.get("status") not in ("completed", "rejected", "cancelled")
        for r in returns
    )
    if active_return:
        return False
    return not any(r.get("status") == "completed" for r in returns)


def _compute_invoice_available(order: dict[str, Any], payment: dict[str, Any]) -> bool:
    if order.get("invoice_requested"):
        return True
    if str(payment.get("status", "")).lower() not in ("captured", "authorized", "refunded"):
        return False
    return order.get("status") in _INVOICE_ELIGIBLE_ORDER_STATUSES


def _compute_refund_status(refunds: list[dict[str, Any]]) -> str:
    if not refunds:
        return "none"
    priority = ("processing", "pending", "approved_awaiting_transfer", "failed", "completed")
    statuses = {str(r.get("status", "")).lower() for r in refunds}
    for status in priority:
        if status in statuses:
            return status
    return str(refunds[-1].get("status", "unknown")).lower()


def _compute_risk_signals(
    order: dict[str, Any],
    payment: dict[str, Any],
    shipment: dict[str, Any],
    returns: list[dict[str, Any]],
    crm_records: list[dict[str, Any]],
) -> dict[str, bool]:
    amount = int(payment.get("amount") or order.get("total_amount") or 0)
    ship_status = str(shipment.get("status") or "").lower()
    pay_status = str(payment.get("status") or "").lower()

    crm_text = " ".join(
        str(ticket.get(k) or "")
        for ticket in crm_records
        for k in ("message_summary", "subject", "intent")
    )
    return_text = " ".join(str(r.get("reason") or "") for r in returns)

    sentiment = _infer_crm_sentiment(crm_records)
    angry = sentiment in ("angry", "frustrated") or any(
        word in crm_text.lower() for word in _ANGRY_KEYWORDS
    )

    damaged = (
        bool(order.get("damage_reported"))
        or order.get("demo_scenario") == "damaged_product"
        or _text_mentions_damaged(return_text, crm_text)
        or any(ticket.get("intent") == "damaged_product" for ticket in crm_records)
    )

    return {
        "high_value_order": amount >= _HIGH_VALUE_THRESHOLD,
        "lost_shipment": ship_status in _LOST_SHIPMENT_STATUSES,
        "damaged_product": damaged,
        "payment_failed": pay_status == "failed" or order.get("status") == "payment_failed",
        "angry_customer": angry,
    }


def _inventory_for_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory_records = load_json_file("inventory.json")
    stock: list[dict[str, Any]] = []
    for item in items:
        product_id = item.get("product_id") or item.get("sku")
        if not product_id:
            continue
        record = find_by_id(inventory_records, "product_id", product_id)
        if record:
            stock.append({
                "product_id": product_id,
                "name": record.get("name"),
                "warehouse": record.get("warehouse"),
                "quantity_available": record.get("quantity_available"),
                "quantity_reserved": record.get("quantity_reserved"),
                "unit_price_inr": record.get("unit_price_inr"),
            })
        else:
            stock.append({
                "product_id": product_id,
                "name": item.get("name"),
                "quantity_available": None,
                "note": "inventory_record_not_found",
            })
    return stock


def _resolve_order(order_id: str, customer_id: str) -> tuple[dict[str, Any] | None, str]:
    orders = load_json_file("orders.json")
    if not orders:
        return None, "none"

    if order_id:
        order = find_by_id(orders, "order_id", order_id)
        if order:
            return order, "order_id"

    if customer_id:
        customer_orders = find_all_by_id(orders, "customer_id", customer_id)
        if customer_orders:
            customer_orders.sort(
                key=lambda o: _parse_date(o.get("placed_on")) or datetime.min,
                reverse=True,
            )
            return customer_orders[0], "customer_id"

    return None, "none"


def build_order_context(order_id: str, customer_id: str = "") -> dict[str, Any]:
    """
    Build a unified order context dict from mock JSON sources.

    Returns an empty dict when the order cannot be resolved.
    """
    order, lookup_method = _resolve_order(order_id, customer_id)
    if not order:
        return {}

    resolved_order_id = order.get("order_id", "")
    resolved_customer_id = order.get("customer_id") or customer_id

    payments = load_json_file("payments.json")
    shipments = load_json_file("shipments.json")
    returns_data = load_json_file("returns.json")
    refunds_data = load_json_file("refunds.json")
    customers = load_json_file("customers.json")
    crm_all = load_json_file("crm_history.json")

    payment = (
        find_by_id(payments, "payment_id", order.get("payment_id"))
        or find_by_id(payments, "order_id", resolved_order_id)
    )
    shipment = (
        find_by_id(shipments, "shipment_id", order.get("shipment_id"))
        or find_by_id(shipments, "order_id", resolved_order_id)
    )
    customer = find_by_id(customers, "customer_id", resolved_customer_id)
    order_returns = find_all_by_id(returns_data, "order_id", resolved_order_id)
    order_refunds = find_all_by_id(refunds_data, "order_id", resolved_order_id)

    crm_for_order = find_all_by_id(crm_all, "order_id", resolved_order_id)
    if not crm_for_order and resolved_customer_id:
        crm_for_customer = find_all_by_id(crm_all, "customer_id", resolved_customer_id)
        crm_for_order = crm_for_customer[:5]

    items = _normalize_items(order.get("items", []))
    payment_summary = _normalize_payment(payment, order)
    shipment_summary = _normalize_shipment(shipment)
    crm_notes = _crm_notes_for_context(crm_for_order)

    return_eligible = _compute_return_eligible(order, order_returns)
    invoice_available = _compute_invoice_available(order, payment_summary)
    refund_status = _compute_refund_status(order_refunds)
    risk_signals = _compute_risk_signals(
        order, payment_summary, shipment_summary, order_returns, crm_for_order
    )

    context: dict[str, Any] = {
        "order_id": resolved_order_id,
        "customer_id": resolved_customer_id,
        "status": order.get("status"),
        "placed_on": order.get("placed_on"),
        "delivered_on": order.get("delivered_on"),
        "expected_delivery": order.get("expected_delivery"),
        "total_amount": order.get("total_amount"),
        "currency": order.get("currency", "INR"),
        "shipping_address": order.get("shipping_address"),
        "coupon_code": order.get("coupon_code"),
        "discount": order.get("discount"),
        "demo_scenario": order.get("demo_scenario"),
        "lookup_method": lookup_method,
        "items": items,
        "payment": payment_summary,
        "shipment": shipment_summary,
        "customer": customer or {},
        "customer_tier": _normalize_tier(
            (customer or {}).get("tier") or order.get("customer_tier")
        ),
        "return_history": order_returns,
        "returns": order_returns,
        "refunds": order_refunds,
        "crm_history": crm_for_order,
        "crm_notes": crm_notes,
        "crm_sentiment": _infer_crm_sentiment(crm_for_order),
        "inventory": _inventory_for_items(items),
        "return_eligible": return_eligible,
        "invoice_available": invoice_available,
        "refund_status": refund_status,
        "risk_signals": risk_signals,
    }

    return context


def _try_extract_order_id(state: AgentState) -> str:
    """Try to get order ID from state or extract from message."""
    order_id = state.get("order_id", "")
    if order_id:
        return order_id

    message = state.get("message", "")
    match = re.search(r"SE\d{4,6}", message, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return ""


def fetch_order_context(state: AgentState) -> AgentState:
    """
    LangGraph node: retrieves order context for the customer.

    Reads: customer_id, order_id, intent, message
    Writes: order_context, order_id, customer_tier, agents_called, audit_trail

    Handles missing data gracefully:
    - If order_id not in state, tries to extract from message
    - If order not found in DB, returns empty context with clear signal
    - Never crashes — always returns valid state update
    """
    customer_id = state.get("customer_id", "")
    order_id = _try_extract_order_id(state)

    order_data = build_order_context(order_id, customer_id)
    lookup_method = order_data.get("lookup_method", "none") if order_data else "none"

    if not order_data:
        return {
            "order_context": {},
            "order_id": "",
            "customer_tier": "regular",
            "agents_called": ["order_context"],
            "audit_trail": [{
                "agent": "order_context",
                "action": "fetch_order",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": f"NOT_FOUND: order_id='{order_id}', customer_id='{customer_id}'",
            }],
        }

    return {
        "order_context": order_data,
        "order_id": order_data.get("order_id", ""),
        "customer_tier": order_data.get("customer_tier", "regular"),
        "agents_called": ["order_context"],
        "audit_trail": [{
            "agent": "order_context",
            "action": "fetch_order",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": (
                f"found via {lookup_method}: order_id={order_data.get('order_id')}, "
                f"status={order_data.get('status')}"
            ),
        }],
    }
