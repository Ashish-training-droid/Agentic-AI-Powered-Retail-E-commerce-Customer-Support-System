# Pallavi's Presentation Script

## Your Parts: Opening + Problem Statement + Demo (Order Tracking)

---

## PART 1: Opening + Problem (You start the presentation) — 2 minutes

### Slides 1-4

**Say:**

> "Good [morning/afternoon]. We are Team E presenting ShopEase — an Agentic AI-Powered Customer Support System.
>
> Let me set the context with the business problem.
>
> [Slide 3]
>
> ShopEase is a fast-growing e-commerce company selling electronics, fashion, home goods, and groceries. They handle thousands of daily customer queries across web, mobile, email, and social.
>
> The problems they face:
> - Customers repeat themselves — there's no shared context across channels
> - Support agents manually search 5+ different systems just to answer one question
> - During festive sales, response times spike because they can't scale fast enough
> - Different agents give different answers about return policies
>
> [Slide 4]
>
> Why can't they just use ChatGPT?
> - It hallucinates — invents return windows that don't exist
> - No grounding — never cites actual company policy
> - No memory — forgets the conversation after each message  
> - No safety — might promise a refund it can't give
>
> That's why we built something different — a multi-agent system where specialized AI agents collaborate. Ashish will show you the architecture."

**[Hand over to Ashish]**

---

## PART 2: Demo — Order Tracking (You start the demo) — 1.5 minutes

### After Ashish explains architecture, you take over for first demo

**Say:**

> "Let me show you this working live.
>
> [In the app - select Rahul Patel (Premium) - CUST_1001]
> [Select scenario: Order Tracking -> Click Send]
>
> Watch what happens. The customer asks 'Where is my order SE10234?'
>
> [Point to the response]
>
> The system responds with the actual tracking number, carrier name BlueDart, and expected delivery date. This isn't generated from nothing — let me show you where this data comes from.
>
> [Expand Agent Console -> Order Context toggle]
>
> This is MY agent — the Order Context Agent. When the customer mentions an order, my code:
> 1. Extracts the order ID 'SE10234' from the message
> 2. Calls the mock Order API to get order status
> 3. Calls the Payment API for payment details
> 4. Calls the Logistics API for shipment tracking
> 5. Calls the CRM API for customer history
> 6. Merges everything into one unified summary
>
> All this data — the carrier name, tracking number, ETA, customer tier — comes from my mock data layer. I built 55 customers, 140+ orders, and 7 API modules totaling over 12,500 lines of realistic data.
>
> The beauty: when this goes to production, you just swap my mock APIs for real Salesforce/SAP calls. The agent code doesn't change."

**[Hand over to Gunjan for next demo]**

---

## Your Code Files (if asked)

```
src/agents/order_context.py — Your agent (extracts order ID, calls APIs, returns unified summary)
src/integrations/mock_apis/ — Your 7 API modules:
  - order_api.py (get_order_status, get_order_details)
  - payment_api.py (get_payment_status)
  - logistics_api.py (get_shipment_tracking)
  - crm_api.py (get_crm_history)
  - inventory_api.py (check_inventory)
  - ticket_api.py (create_ticket)
  - return_api.py (create_return_request)
data/mock/ — Your 8 JSON data files (orders, payments, shipments, customers, CRM, returns, refunds, inventory)
```
