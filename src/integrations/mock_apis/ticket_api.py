"""
Mock Support Ticket API (Person 3).

Session tickets created via create_ticket are stored in memory for the process lifetime.
Existing tickets are also read from crm_history.json.
"""

from __future__ import annotations

from typing import Any

from src.integrations.mock_apis import (
    error_response,
    find_by_id,
    load_json_file,
    ok_response,
    utc_timestamp,
)

_session_tickets: dict[str, dict[str, Any]] = {}


def _next_ticket_id(order_id: str | None) -> str:
    if order_id and order_id.startswith("SE"):
        return f"TKT_{order_id.replace('SE', '')}_{len(_session_tickets) + 1}"
    return f"TKT_NEW_{len(_session_tickets) + 10001}"


def _find_ticket(ticket_id: str) -> dict[str, Any] | None:
    ticket_id = (ticket_id or "").strip()
    if ticket_id in _session_tickets:
        return dict(_session_tickets[ticket_id])

    crm = load_json_file("crm_history.json")
    record = find_by_id(crm, "ticket_id", ticket_id)
    if record:
        return dict(record)
    return None


def create_ticket(
    customer_id: str,
    order_id: str,
    issue_type: str,
    priority: str = "medium",
    description: str = "",
) -> dict[str, Any]:
    """Create a new support ticket (in-memory mock)."""
    customer_id = (customer_id or "").strip().upper()
    order_id = (order_id or "").strip().upper()
    issue_type = (issue_type or "general").strip()

    if not customer_id:
        return error_response("customer_id is required")

    if not find_by_id(load_json_file("customers.json"), "customer_id", customer_id):
        return error_response(f"Customer {customer_id} not found")

    if order_id:
        order = find_by_id(load_json_file("orders.json"), "order_id", order_id)
        if not order:
            return error_response(f"Order {order_id} not found")

    ticket_id = _next_ticket_id(order_id or None)
    priority = (priority or "medium").lower()
    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "order_id": order_id or None,
        "issue_type": issue_type,
        "intent": issue_type,
        "priority": priority,
        "status": "open",
        "channel": "api",
        "subject": description[:120] if description else f"{issue_type.replace('_', ' ').title()} request",
        "message_summary": description or f"Ticket created for {issue_type}.",
        "created_on": utc_timestamp()[:10],
        "updated_on": utc_timestamp()[:10],
        "notes": [],
    }
    _session_tickets[ticket_id] = ticket

    data = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "order_id": order_id or None,
        "issue_type": issue_type,
        "priority": priority,
        "status": "open",
        "message": f"Ticket {ticket_id} created successfully.",
    }
    return ok_response(data)


def get_ticket_status(ticket_id: str) -> dict[str, Any]:
    """Retrieve ticket status by ticket_id."""
    ticket_id = (ticket_id or "").strip()
    if not ticket_id:
        return error_response("ticket_id is required")

    ticket = _find_ticket(ticket_id)
    if not ticket:
        return error_response(f"Ticket {ticket_id} not found")

    data = {
        "ticket_id": ticket.get("ticket_id"),
        "customer_id": ticket.get("customer_id"),
        "order_id": ticket.get("order_id"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "issue_type": ticket.get("issue_type") or ticket.get("intent"),
        "subject": ticket.get("subject"),
        "created_on": ticket.get("created_on"),
        "updated_on": ticket.get("updated_on"),
        "notes": ticket.get("notes", []),
    }
    return ok_response(data)


def update_ticket(ticket_id: str, status: str, note: str = "") -> dict[str, Any]:
    """Update ticket status and append an optional note."""
    ticket_id = (ticket_id or "").strip()
    status = (status or "").strip().lower()

    if not ticket_id:
        return error_response("ticket_id is required")
    if not status:
        return error_response("status is required")

    ticket = _find_ticket(ticket_id)
    if not ticket:
        return error_response(f"Ticket {ticket_id} not found")

    ticket["status"] = status
    ticket["updated_on"] = utc_timestamp()[:10]
    if note:
        notes = list(ticket.get("notes") or [])
        notes.append({"at": utc_timestamp(), "note": note})
        ticket["notes"] = notes

    if ticket_id in _session_tickets:
        _session_tickets[ticket_id] = ticket
    else:
        _session_tickets[ticket_id] = ticket

    data = {
        "ticket_id": ticket_id,
        "status": status,
        "message": f"Ticket {ticket_id} updated to {status}.",
        "note_added": bool(note),
    }
    return ok_response(data)
