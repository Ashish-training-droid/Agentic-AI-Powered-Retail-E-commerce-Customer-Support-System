"""
Mock CRM API (Person 3).
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import (
    error_response,
    find_all_by_id,
    find_by_id,
    load_json_file,
    ok_response,
)


def get_crm_history(customer_id: str) -> dict[str, Any]:
    """Retrieve CRM tickets and interaction history for a customer."""
    customer_id = (customer_id or "").strip().upper()
    if not customer_id:
        return error_response("customer_id is required")

    customers = load_json_file("customers.json")
    if not find_by_id(customers, "customer_id", customer_id):
        return error_response(f"Customer {customer_id} not found")

    tickets = find_all_by_id(load_json_file("crm_history.json"), "customer_id", customer_id)
    tickets.sort(key=lambda t: t.get("created_on", ""), reverse=True)

    notes = []
    for ticket in tickets:
        summary = ticket.get("message_summary") or ticket.get("subject") or ""
        if summary:
            created = ticket.get("created_on", "")
            notes.append(f"{created}: {summary}".strip(": "))

    data = {
        "customer_id": customer_id,
        "ticket_count": len(tickets),
        "tickets": tickets,
        "crm_notes": notes,
    }
    return ok_response(data)


def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Retrieve customer profile and tier."""
    customer_id = (customer_id or "").strip().upper()
    if not customer_id:
        return error_response("customer_id is required")

    customer = find_by_id(load_json_file("customers.json"), "customer_id", customer_id)
    if not customer:
        return error_response(f"Customer {customer_id} not found")

    tier = customer.get("tier", "standard")
    if str(tier).lower() == "standard":
        tier_display = "regular"
    else:
        tier_display = tier

    data = {
        "customer_id": customer.get("customer_id"),
        "name": customer.get("name"),
        "email": customer.get("email"),
        "phone": customer.get("phone"),
        "tier": tier,
        "customer_tier": tier_display,
        "city": customer.get("city"),
        "state": customer.get("state"),
        "pincode": customer.get("pincode"),
        "address_line1": customer.get("address_line1"),
        "address_line2": customer.get("address_line2"),
        "registered_on": customer.get("registered_on"),
        "loyalty_points": customer.get("loyalty_points"),
        "preferred_language": customer.get("preferred_language"),
    }
    return ok_response(data)
