"""
Order Context Agent (Pallavi (Person 3))

Retrieves unified order, shipment, payment, return, and CRM history
via src/integrations/mock_apis/ and assembles order_context for downstream agents.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.integrations.mock_apis import find_all_by_id, find_by_id, load_json_file
from src.integrations.mock_apis.crm_api import get_crm_history, get_customer_profile
from src.integrations.mock_apis.inventory_api import check_inventory
from src.integrations.mock_apis.logistics_api import get_shipment_tracking
from src.integrations.mock_apis.order_api import get_order_details, get_order_status
from src.integrations.mock_apis.payment_api import get_payment_status
from src.integrations.mock_apis.return_api import get_return_status
from src.orchestrator.state import AgentState

_HIGH_VALUE_THRESHOLD = 100_000
_LOST_SHIPMENT_STATUSES = frozenset({"lost", "lost_in_transit"})
_DAMAGED_KEYWORDS = (
    "damaged", "damage", "broken", "cracked", "defective", "defect",
)
_ANGRY_KEYWORDS = ("angry", "frustrated", "furious", "extremely frustrated", "upset")
_INVOICE_ELIGIBLE_ORDER_STATUSES = frozenset(
    {"shipped", "delivered", "returned", "refund_initiated"}
)


def _api_data(response: dict[str, Any] | None) -> dict[str, Any]:
    if not response or not response.get("success"):
        return {}
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def _normalize_tier(tier: str | None) -> str:
    if not tier:
        return "regular"
    tier_lower = tier.lower()
    if tier_lower == "standard":
        return "regular"
    return tier_lower


def _normalize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _normalize_payment(payment: dict[str, Any], order: dict[str, Any]) -> dict[str, Any]:
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


def _normalize_shipment(shipment: dict[str, Any]) -> dict[str, Any]:
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


def _crm_notes_for_context(crm_records: list[dict[str, Any]], fallback_notes: list[str]) -> list[str]:
    if fallback_notes:
        return list(fallback_notes)
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
        sentiment = str(ticket.get("sentiment") or "").lower()
        if sentiment in ("angry", "frustrated", "negative"):
            return sentiment
        text = " ".join(
            str(ticket.get(k) or "")
            for k in ("message_summary", "subject", "intent")
        ).lower()
        if any(word in text for word in _ANGRY_KEYWORDS):
            return "frustrated"
        if ticket.get("intent") == "damaged_product":
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
    stock: list[dict[str, Any]] = []
    for item in items:
        product_id = item.get("product_id") or item.get("sku")
        if not product_id:
            continue
        inv_resp = check_inventory(str(product_id))
        inv = _api_data(inv_resp)
        if inv:
            stock.append({
                "product_id": product_id,
                "name": inv.get("name") or item.get("name"),
                "warehouse": inv.get("warehouse"),
                "quantity_available": inv.get("quantity_available"),
                "quantity_reserved": inv.get("quantity_reserved"),
                "unit_price_inr": inv.get("unit_price_inr"),
            })
        else:
            stock.append({
                "product_id": product_id,
                "name": item.get("name"),
                "quantity_available": None,
                "note": "inventory_record_not_found",
            })
    return stock


def _resolve_order_id(order_id: str, customer_id: str) -> tuple[str, str]:
    """
    Resolve an order_id and lookup_method using APIs and mock data helpers.

    Returns:
        (resolved_order_id, lookup_method)
    """
    order_id = (order_id or "").strip().upper()
    customer_id = (customer_id or "").strip().upper()

    if order_id:
        details = get_order_details(order_id)
        if details.get("success"):
            return order_id, "order_id"
        status_resp = get_order_status(order_id)
        if status_resp.get("success"):
            return order_id, "order_id"

    if customer_id:
        orders = find_all_by_id(load_json_file("orders.json"), "customer_id", customer_id)
        if orders:
            orders.sort(
                key=lambda o: _parse_date(o.get("placed_on")) or datetime.min,
                reverse=True,
            )
            return str(orders[0].get("order_id", "")), "customer_id"

        crm_resp = get_crm_history(customer_id)
        if crm_resp.get("success"):
            tickets = crm_resp.get("data", {}).get("tickets") or []
            for ticket in tickets:
                tid = ticket.get("order_id")
                if tid:
                    details = get_order_details(str(tid))
                    if details.get("success"):
                        return str(tid).upper(), "customer_id"

    return "", "none"


def build_order_context(order_id: str, customer_id: str = "") -> dict[str, Any]:
    """
    Build a unified order context dict using mock API integrations.

    Returns an empty dict when the order cannot be resolved.
    """
    resolved_id, lookup_method = _resolve_order_id(order_id, customer_id)
    if not resolved_id:
        return {}

    details_resp = get_order_details(resolved_id)
    order = _api_data(details_resp)
    if not order:
        return {}

    resolved_customer_id = str(order.get("customer_id") or customer_id or "").upper()

    payment_resp = get_payment_status(order_id=resolved_id)
    payment_raw = _api_data(payment_resp)

    shipment_resp = get_shipment_tracking(order_id=resolved_id)
    shipment_raw = _api_data(shipment_resp)

    return_resp = get_return_status(order_id=resolved_id)
    return_raw = _api_data(return_resp)
    order_returns = find_all_by_id(load_json_file("returns.json"), "order_id", resolved_id)
    if return_raw and not any(r.get("return_id") == return_raw.get("return_id") for r in order_returns):
        order_returns = order_returns + [return_raw]

    order_refunds = find_all_by_id(load_json_file("refunds.json"), "order_id", resolved_id)

    crm_records: list[dict[str, Any]] = []
    crm_notes: list[str] = []
    crm_resp: dict[str, Any] | None = None
    if resolved_customer_id:
        crm_resp = get_crm_history(resolved_customer_id)
        if crm_resp.get("success"):
            crm_data = crm_resp.get("data") or {}
            crm_notes = list(crm_data.get("crm_notes") or [])
            all_tickets = list(crm_data.get("tickets") or [])
            crm_records = [
                t for t in all_tickets
                if t.get("order_id") in (resolved_id, None) or not t.get("order_id")
            ]
            if not crm_records:
                crm_records = all_tickets[:5]

    customer: dict[str, Any] = {}
    if resolved_customer_id:
        profile_resp = get_customer_profile(resolved_customer_id)
        if profile_resp.get("success"):
            customer = _api_data(profile_resp)

    items = _normalize_items(order.get("items", []))
    payment_summary = _normalize_payment(payment_raw, order)
    shipment_summary = _normalize_shipment(shipment_raw)
    notes = _crm_notes_for_context(crm_records, crm_notes)

    return_eligible = _compute_return_eligible(order, order_returns)
    invoice_available = _compute_invoice_available(order, payment_summary)
    refund_status = _compute_refund_status(order_refunds)
    risk_signals = _compute_risk_signals(
        order, payment_summary, shipment_summary, order_returns, crm_records
    )

    return {
        "order_id": resolved_id,
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
        "customer": customer,
        "customer_tier": _normalize_tier(
            customer.get("customer_tier") or customer.get("tier")
        ),
        "return_history": order_returns,
        "returns": order_returns,
        "refunds": order_refunds,
        "crm_history": crm_records,
        "crm_notes": notes,
        "crm_sentiment": _infer_crm_sentiment(crm_records),
        "inventory": _inventory_for_items(items),
        "return_eligible": return_eligible,
        "invoice_available": invoice_available,
        "refund_status": refund_status,
        "risk_signals": risk_signals,
        "api_errors": _collect_api_errors(
            details_resp, payment_resp, shipment_resp, return_resp, crm_resp
        ),
    }


def _collect_api_errors(*responses: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    for resp in responses:
        if resp and not resp.get("success"):
            err = resp.get("error")
            if err:
                errors.append(str(err))
    return errors


def _try_extract_order_id(state: AgentState) -> str:
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

    try:
        order_data = build_order_context(order_id, customer_id)
    except Exception:
        order_data = {}

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

    audit_details = (
        f"found via {lookup_method}: order_id={order_data.get('order_id')}, "
        f"status={order_data.get('status')}"
    )
    api_errors = order_data.get("api_errors") or []
    if api_errors:
        audit_details += f"; api_warnings={len(api_errors)}"

    return {
        "order_context": order_data,
        "order_id": order_data.get("order_id", ""),
        "customer_tier": order_data.get("customer_tier", "regular"),
        "agents_called": ["order_context"],
        "audit_trail": [{
            "agent": "order_context",
            "action": "fetch_order",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": audit_details,
        }],
    }
