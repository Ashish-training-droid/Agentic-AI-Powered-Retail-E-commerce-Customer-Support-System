# Pallavi (Person 3): Mock API + Workflow Automation Engineer

## Your Role

You own the **integration layer** — mock APIs that simulate real backend systems (orders, payments, logistics, inventory, CRM, tickets). You also build the **Workflow Automation Agent** that executes self-service actions.

## What You Need to Build

### 1. Mock Data (Week 1-2)

Create realistic mock data in `data/mock/`. Every demo scenario needs matching data.

**Files to create:**

```
data/mock/
├── orders.json          # 10-15 orders with different statuses
├── payments.json        # Payment records for each order
├── shipments.json       # Tracking info, carrier, status, ETA
├── inventory.json       # Product stock levels
├── returns.json         # Return request records
├── tickets.json         # Support ticket history
├── crm_history.json     # Customer contact history
└── customers.json       # Customer profiles and tiers
```

**Order data structure (orders.json):**

```json
[
  {
    "order_id": "SE10234",
    "customer_id": "CUST_1001",
    "status": "shipped",
    "placed_on": "2026-05-15",
    "items": [
      {
        "item_id": "ITEM_001",
        "product_id": "WH-100",
        "name": "Wireless Headphones",
        "quantity": 1,
        "price": 2499,
        "category": "electronics"
      }
    ],
    "total_amount": 2499,
    "shipping_address": "123 MG Road, Bangalore 560001",
    "payment_id": "PAY_10234",
    "shipment_id": "SHIP_10234"
  }
]
```

**Make sure these customer/order IDs exist (used in demos):**
- CUST_1001 -> SE10234 (shipped, headphones)
- CUST_1002 -> SE10567 (delivered, shoes)
- CUST_1003 -> SE10890 (delivered, Samsung Galaxy S24, high value)
- CUST_1004 -> SE10111 (processing, laptop)

### 2. Mock API Functions (Week 2)

Create `src/integrations/mock_apis/` with tool functions:

```
src/integrations/mock_apis/
├── __init__.py
├── order_api.py        # get_order_status, get_order_details
├── payment_api.py      # get_payment_status, process_refund
├── logistics_api.py    # get_shipment_tracking, get_delivery_eta
├── inventory_api.py    # check_inventory, get_stock_level
├── crm_api.py          # get_crm_history, get_customer_profile
├── ticket_api.py       # create_ticket, get_ticket_status, update_ticket
└── return_api.py       # create_return_request, get_return_status, cancel_return
```

**Each function must:**
- Accept clear parameters (order_id, customer_id, etc.)
- Return structured JSON with a `success` field
- Handle "not found" cases gracefully
- Include a timestamp in the response

**Example:**

```python
def get_order_status(order_id: str) -> dict:
    """
    Retrieve current order status and summary.
    
    Returns:
        {
            "success": True,
            "order_id": "SE10234",
            "status": "shipped",
            "items": [...],
            "payment_status": "captured",
            "shipment_status": "in_transit",
            "eta": "2026-05-22"
        }
    """
    orders = _load_orders()
    order = next((o for o in orders if o["order_id"] == order_id), None)
    if not order:
        return {"success": False, "error": f"Order {order_id} not found"}
    return {"success": True, **order}
```

### 3. Order Context Agent (Week 2-3)

**Your main code file:** `src/agents/order_context.py`

Replace the mock implementation. This agent collects data from MULTIPLE APIs and creates a unified summary.

**What it should do:**

```python
def fetch_order_context(state: AgentState) -> AgentState:
    # 1. Get customer_id and order_id from state
    # 2. Call get_order_status(order_id)
    # 3. Call get_payment_status(payment_id)
    # 4. Call get_shipment_tracking(shipment_id)
    # 5. Call get_crm_history(customer_id)
    # 6. Call get_return_status(order_id) if relevant
    # 7. Merge into unified order_context dict
    # 8. Return updated state
```

**Output format (must return this):**

```python
{
    "order_context": {
        "order_id": "SE10234",
        "status": "shipped",
        "items": [...],
        "payment": {"method": "UPI", "status": "captured", "amount": 2499},
        "shipment": {"carrier": "BlueDart", "tracking": "BD98712", "status": "in_transit", "eta": "2026-05-22"},
        "return_history": [],
        "crm_notes": ["Called about delivery delay on 2026-05-18"],
        "customer_tier": "premium"
    },
    "order_id": "SE10234",
    "customer_tier": "premium",
    "agents_called": ["order_context"],
    "audit_trail": [...]
}
```

### 4. Workflow Automation Agent (Week 3)

**Your main code file:** `src/agents/workflow_automation.py`

Replace the mock implementation. Build real workflow logic:

| Workflow | Trigger | Steps |
|----------|---------|-------|
| `initiate_return` | return_request | Check eligibility (policy) -> Validate item -> Create return -> Schedule pickup |
| `check_refund` | refund_status | Get payment record -> Check refund processing -> Return timeline |
| `send_invoice` | order_tracking | Get order -> Generate invoice link -> Return URL |
| `create_ticket` | damaged_product, escalation | Collect context -> Assign priority -> Create ticket -> Return ticket ID |
| `update_address` | delivery_complaint | Check shipment status -> If not shipped, update -> Confirm |

**Each workflow must:**
- Check preconditions before acting
- Return success/failure with clear message
- Mark sensitive actions (refund > 5000) as requiring human approval
- Log the action in audit trail

### 5. Action Guardrails (Week 4)

Add safety checks in `src/integrations/mock_apis/guardrails.py`:

```python
SENSITIVE_ACTIONS = {
    "process_refund": {"threshold": 5000, "approval": "finance"},
    "cancel_order": {"threshold": 0, "approval": "senior_agent"},
    "override_policy": {"threshold": 0, "approval": "manager"},
}

def requires_approval(action: str, amount: float = 0) -> tuple[bool, str]:
    """Check if action needs human approval before execution."""
    ...
```

## How to Test Your Work

```bash
# Run demos that use your agents
python -m src.main --demo 1   # Order tracking (uses order_context)
python -m src.main --demo 2   # Return request (uses order_context + workflow)
python -m src.main --demo 4   # Damaged product (uses order_context + workflow)
python -m src.main --demo 6   # Refund status (uses order_context)
```

## Handoff Partners

- **Ashish (Person 1) (you report to):** Your order_context feeds into Response Generator and Evaluator
- **Aditi (Person 4) (uses your APIs):** Product Advisory may check inventory via your API
- **Rohan (Person 5) (uses your output):** Risk agent checks order value and payment disputes

## Quality Checklist

- [ ] All 4 demo customer/order IDs have complete data
- [ ] Mock APIs return consistent data (order -> payment -> shipment all linked)
- [ ] get_order_status handles "not found" gracefully
- [ ] Return workflow checks policy eligibility before creating return
- [ ] Sensitive actions (refund > 5000) are flagged for human approval
- [ ] Every API call returns a `success` boolean
- [ ] CRM history shows realistic interaction records
- [ ] Workflow actions produce audit trail entries
