"""
Order Context Agent (Pallavi (Person 3))

Retrieves unified order, shipment, payment, invoice, return, and CRM history
for a given customer/order. Returns a structured summary that other agents use.

TODO(Pallavi (Person 3)): Replace mock data with actual retrieval logic using mock APIs.
Currently returns hardcoded sample data for demo purposes.
"""

from __future__ import annotations
from datetime import datetime, timezone

from src.orchestrator.state import AgentState


# Mock order database — Pallavi (Person 3) will replace with mock_apis integration
MOCK_ORDERS = {
    "SE10234": {
        "order_id": "SE10234",
        "status": "shipped",
        "items": [{"name": "Wireless Headphones", "sku": "WH-100", "qty": 1, "price": 2499}],
        "payment": {"method": "UPI", "status": "captured", "amount": 2499},
        "shipment": {"carrier": "BlueDart", "tracking": "BD98712", "status": "in_transit", "eta": "2026-05-22"},
        "return_history": [],
        "crm_notes": ["Called about delivery delay on 2026-05-18"],
        "customer_tier": "premium",
    },
    "SE10567": {
        "order_id": "SE10567",
        "status": "delivered",
        "items": [{"name": "Running Shoes - Nike Air", "sku": "RS-NIKE-42", "qty": 1, "price": 8999}],
        "payment": {"method": "Credit Card", "status": "captured", "amount": 8999},
        "shipment": {"carrier": "Delhivery", "tracking": "DL45678", "status": "delivered", "delivered_on": "2026-05-17"},
        "return_history": [],
        "crm_notes": [],
        "customer_tier": "regular",
    },
    "SE10890": {
        "order_id": "SE10890",
        "status": "delivered",
        "items": [{"name": "Samsung Galaxy S24", "sku": "SGS24-256", "qty": 1, "price": 74999}],
        "payment": {"method": "EMI", "status": "captured", "amount": 74999},
        "shipment": {"carrier": "BlueDart", "tracking": "BD11223", "status": "delivered", "delivered_on": "2026-05-15"},
        "return_history": [],
        "crm_notes": ["Reported screen crack on 2026-05-19"],
        "customer_tier": "vip",
    },
    "SE10111": {
        "order_id": "SE10111",
        "status": "processing",
        "items": [
            {"name": "HP Pavilion Laptop 15", "sku": "HP-PAV-15", "qty": 1, "price": 55999},
            {"name": "Laptop Sleeve", "sku": "LS-15", "qty": 1, "price": 799},
        ],
        "payment": {"method": "Debit Card", "status": "captured", "amount": 56798},
        "shipment": {"carrier": "DTDC", "tracking": None, "status": "not_shipped", "eta": "2026-05-24"},
        "return_history": [],
        "crm_notes": [],
        "customer_tier": "regular",
    },
}

# Map customer IDs to order IDs
MOCK_CUSTOMER_ORDERS = {
    "CUST_1001": ["SE10234"],
    "CUST_1002": ["SE10567"],
    "CUST_1003": ["SE10890"],
    "CUST_1004": ["SE10111"],
}


def _try_extract_order_id(state: AgentState) -> str:
    """Try to get order ID from state or extract from message."""
    order_id = state.get("order_id", "")
    if order_id:
        return order_id

    # Try extracting from message
    import re
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

    TODO(Pallavi (Person 3)): Replace mock lookup with calls to:
      - get_order_status(order_id)
      - get_payment_status(order_id)
      - get_shipment_tracking(order_id)
      - get_crm_history(customer_id)
      - get_return_status(order_id)
    """
    customer_id = state.get("customer_id", "")
    order_id = _try_extract_order_id(state)

    order_data = {}
    lookup_method = "none"

    # Strategy 1: Direct order_id lookup
    if order_id and order_id in MOCK_ORDERS:
        order_data = MOCK_ORDERS[order_id]
        lookup_method = "order_id"

    # Strategy 2: Fall back to customer's most recent order
    elif customer_id:
        customer_orders = MOCK_CUSTOMER_ORDERS.get(customer_id, [])
        if customer_orders:
            order_data = MOCK_ORDERS.get(customer_orders[0], {})
            lookup_method = "customer_id"

    # Strategy 3: Nothing found — return empty with clear signal
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
            "details": f"found via {lookup_method}: order_id={order_data.get('order_id')}, status={order_data.get('status')}",
        }],
    }
