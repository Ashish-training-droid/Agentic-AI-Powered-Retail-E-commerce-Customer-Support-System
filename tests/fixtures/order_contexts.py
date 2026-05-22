"""
Named order_context fixtures for Rohan (Person 5) tests.

Each factory returns a dictionary that matches the ``order_context`` schema
defined in ``src.orchestrator.state.AgentState`` and produced by Pallavi (Person 3)'s
``src.agents.order_context.fetch_order_context``.

Using factories (not fixed dicts) keeps tests hermetic: callers can override
any field via keyword arguments without leaking state between tests.

Schema contract (Pallavi (Person 3) ↔ Rohan (Person 5))
-------------------------------------
order_context = {
    "order_id":         str,
    "status":           "processing" | "shipped" | "in_transit" | "delivered" | "cancelled",
    "items":            list[{"name": str, "sku": str, "qty": int, "price": int}],
    "payment":          {"method": str, "status": str, "amount": int},
    "shipment":         {"carrier": str, "tracking": str | None,
                         "status": "not_shipped" | "in_transit" | "delivered" | "lost",
                         "eta": str | None, "delivered_on": str | None},
    "return_history":   list[dict],
    "crm_notes":        list[str],
    "customer_tier":    "regular" | "premium" | "vip",
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderContextFactory:
    """Builder for an order_context dict.

    Use ``OrderContextFactory(...).build()`` for ad-hoc combinations, or the
    pre-named helpers below for the common scenarios Rohan (Person 5) tests against.
    """

    order_id: str = "SE99999"
    status: str = "delivered"
    item_name: str = "Generic Item"
    sku: str = "GEN-001"
    qty: int = 1
    price: int = 1000
    payment_method: str = "UPI"
    payment_status: str = "captured"
    payment_amount: int | None = None
    carrier: str = "BlueDart"
    tracking: str | None = "BD00000"
    shipment_status: str = "delivered"
    eta: str | None = None
    delivered_on: str | None = "2026-05-15"
    return_history: list[dict] = field(default_factory=list)
    crm_notes: list[str] = field(default_factory=list)
    customer_tier: str = "regular"

    def build(self) -> dict[str, Any]:
        amount = self.payment_amount if self.payment_amount is not None else self.price * self.qty
        ctx: dict[str, Any] = {
            "order_id": self.order_id,
            "status": self.status,
            "items": [
                {"name": self.item_name, "sku": self.sku, "qty": self.qty, "price": self.price}
            ],
            "payment": {
                "method": self.payment_method,
                "status": self.payment_status,
                "amount": amount,
            },
            "shipment": {
                "carrier": self.carrier,
                "tracking": self.tracking,
                "status": self.shipment_status,
            },
            "return_history": list(self.return_history),
            "crm_notes": list(self.crm_notes),
            "customer_tier": self.customer_tier,
        }
        if self.eta is not None:
            ctx["shipment"]["eta"] = self.eta
        if self.delivered_on is not None and self.shipment_status == "delivered":
            ctx["shipment"]["delivered_on"] = self.delivered_on
        return ctx


def empty_context() -> dict[str, Any]:
    """Customer reached us with no recoverable order (no ID, not in DB)."""
    return {}


def regular_in_transit() -> dict[str, Any]:
    """Routine low-value order on the way — baseline 'should not escalate' case."""
    return OrderContextFactory(
        order_id="SE20001",
        status="shipped",
        item_name="Wireless Earbuds",
        sku="WH-102",
        price=1499,
        carrier="Delhivery",
        tracking="DL10001",
        shipment_status="in_transit",
        eta="2026-05-23",
        delivered_on=None,
        customer_tier="regular",
    ).build()


def premium_in_transit() -> dict[str, Any]:
    """Premium tier customer, moderate-value order, in transit."""
    return OrderContextFactory(
        order_id="SE20002",
        status="shipped",
        item_name="Sony WH-1000XM5",
        sku="WH-100",
        price=24999,
        carrier="BlueDart",
        tracking="BD20002",
        shipment_status="in_transit",
        eta="2026-05-24",
        delivered_on=None,
        customer_tier="premium",
    ).build()


def vip_high_value_in_transit() -> dict[str, Any]:
    """VIP customer, high-value laptop, in transit — VIP escalation threshold."""
    return OrderContextFactory(
        order_id="SE20003",
        status="shipped",
        item_name="MacBook Air M3",
        sku="LP-200",
        price=114900,
        carrier="BlueDart",
        tracking="BD20003",
        shipment_status="in_transit",
        eta="2026-05-22",
        delivered_on=None,
        customer_tier="vip",
    ).build()


def damaged_low_value() -> dict[str, Any]:
    """Damaged item under high-value threshold — should NOT trigger replacement team."""
    return OrderContextFactory(
        order_id="SE20004",
        status="delivered",
        item_name="JBL Tune 770NC",
        sku="WH-102",
        price=7999,
        carrier="Delhivery",
        tracking="DL20004",
        shipment_status="delivered",
        delivered_on="2026-05-18",
        crm_notes=["Customer reported damaged packaging on 2026-05-19"],
        customer_tier="regular",
    ).build()


def damaged_vip_high_value() -> dict[str, Any]:
    """VIP + damaged + high-value — multi-factor trigger, should escalate at P1/P2."""
    return OrderContextFactory(
        order_id="SE20005",
        status="delivered",
        item_name="Samsung Galaxy S24",
        sku="PH-301",
        price=74999,
        carrier="BlueDart",
        tracking="BD20005",
        shipment_status="delivered",
        delivered_on="2026-05-15",
        crm_notes=["Reported screen crack on 2026-05-19"],
        customer_tier="vip",
    ).build()


def lost_high_value_shipment() -> dict[str, Any]:
    """Shipment marked lost — single-factor escalation to logistics."""
    return OrderContextFactory(
        order_id="SE20006",
        status="shipped",
        item_name="ASUS ROG Strix G16",
        sku="LP-204",
        price=154990,
        carrier="DTDC",
        tracking="DT20006",
        shipment_status="lost",
        eta="2026-05-19",
        delivered_on=None,
        customer_tier="premium",
    ).build()


def angry_repeated_contact() -> dict[str, Any]:
    """Four CRM contacts on the same issue — repeated-contact escalation signal."""
    return OrderContextFactory(
        order_id="SE20007",
        status="delivered",
        item_name="Apple iPad Air M2",
        sku="TB-350",
        price=59900,
        carrier="BlueDart",
        tracking="BD20007",
        shipment_status="delivered",
        delivered_on="2026-05-10",
        crm_notes=[
            "Called about screen flicker on 2026-05-12",
            "Followed up — issue persists on 2026-05-15",
            "Escalation requested on 2026-05-18",
            "Pressing for resolution on 2026-05-20",
        ],
        customer_tier="regular",
    ).build()


def fraud_signal_duplicate_refund() -> dict[str, Any]:
    """Multiple recent refunds on the same account — fraud-review signal."""
    return OrderContextFactory(
        order_id="SE20008",
        status="delivered",
        item_name="iPhone 15",
        sku="PH-300",
        price=79900,
        payment_method="Credit Card",
        carrier="BlueDart",
        tracking="BD20008",
        shipment_status="delivered",
        delivered_on="2026-05-08",
        return_history=[
            {"order_id": "SE19990", "status": "refunded", "amount": 79900, "date": "2026-04-12"},
            {"order_id": "SE19995", "status": "refunded", "amount": 64999, "date": "2026-04-28"},
            {"order_id": "SE20002", "status": "refunded", "amount": 24999, "date": "2026-05-10"},
        ],
        customer_tier="regular",
    ).build()


def payment_disputed_card() -> dict[str, Any]:
    """Captured payment with a chargeback flag — routes to refund_specialist."""
    return OrderContextFactory(
        order_id="SE20009",
        status="delivered",
        item_name="Dell XPS 13",
        sku="LP-201",
        price=109990,
        payment_method="Credit Card",
        payment_status="disputed",
        carrier="Delhivery",
        tracking="DL20009",
        shipment_status="delivered",
        delivered_on="2026-04-30",
        crm_notes=["Customer raised chargeback via issuer on 2026-05-15"],
        customer_tier="premium",
    ).build()


def delivered_no_issue() -> dict[str, Any]:
    """Plain delivered order, no signals — negative control for false-positive tests."""
    return OrderContextFactory(
        order_id="SE20010",
        status="delivered",
        item_name="Levi's 511 Slim Jeans",
        sku="FA-500",
        price=2799,
        carrier="Delhivery",
        tracking="DL20010",
        shipment_status="delivered",
        delivered_on="2026-05-17",
        customer_tier="regular",
    ).build()
