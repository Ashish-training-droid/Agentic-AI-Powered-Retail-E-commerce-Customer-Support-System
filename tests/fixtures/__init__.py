"""Test fixtures owned by Rohan (Person 5) (escalation, QA, evaluation).

Centralizing fixtures here means Pallavi (Person 3) changing the order_context
implementation cannot break Rohan (Person 5)'s unit tests or evaluation harness;
both consume the same schema-compliant dictionaries from this module.
"""

from tests.fixtures.order_contexts import (
    OrderContextFactory,
    angry_repeated_contact,
    damaged_low_value,
    damaged_vip_high_value,
    delivered_no_issue,
    empty_context,
    fraud_signal_duplicate_refund,
    lost_high_value_shipment,
    payment_disputed_card,
    premium_in_transit,
    regular_in_transit,
    vip_high_value_in_transit,
)

__all__ = [
    "OrderContextFactory",
    "angry_repeated_contact",
    "damaged_low_value",
    "damaged_vip_high_value",
    "delivered_no_issue",
    "empty_context",
    "fraud_signal_duplicate_refund",
    "lost_high_value_shipment",
    "payment_disputed_card",
    "premium_in_transit",
    "regular_in_transit",
    "vip_high_value_in_transit",
]
