# ShopEase Agentic AI — Person 4 Module

Customer chat UI, agent-assist console, and Product Advisory Agent for the
ShopEase Retail & E-commerce Customer Support Capstone Project.

This module is built and owned by **Person 4** (UI / UX + Product Advisory).
The other agents (intent, policy, order, workflow, risk, evaluator) are
**mocked locally** so the UI can run end-to-end during development, and will
be swapped out for real implementations from Persons 1, 2, 3 and 5.

---

## 1. Quick start

```bash
# from inside shopease_capstone/
pip install streamlit pandas
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Requirements
- Python 3.10+
- `streamlit >= 1.30`
- `pandas >= 2.0`

---

## 2. Project structure

```
shopease_capstone/
├── app.py                          # Streamlit entry point
├── DEMO_SCRIPT.md                  # Line-by-line script for the final demo
├── data/
│   ├── products.csv                # Product catalog (laptops, phones, headphones, accessories)
│   ├── orders.json                 # Mock orders covering all 7 demo scenarios
│   └── policies.json               # Return / refund / warranty / delivery / coupon rules
├── modules/
│   ├── __init__.py
│   ├── mock_agents.py              # All 7 simulated agents + orchestrator wrapper
│   ├── product_advisory.py         # Person 4's signature Product Advisory Agent
│   └── ui_components.py            # Reusable panels for the agent console
└── README.md
```

---

## 3. Public agent functions

These are the names other teammates code against. Each is documented inside
its module — comments explain the inputs, outputs, and where to swap in a
real implementation later.

| Function | Lives in | Real owner |
|---|---|---|
| `classify_intent(query)` | `mock_agents.py` | Person 1 |
| `get_order_context(order_id, query)` | `mock_agents.py` | Person 3 |
| `retrieve_policy(intent, query)` | `mock_agents.py` | Person 2 |
| `automate_workflow(intent, order_ctx)` | `mock_agents.py` | Person 3 |
| `assess_risk(query, intent_out, order_ctx)` | `mock_agents.py` | Person 5 |
| `generate_response(query, agent_outputs)` | `mock_agents.py` | Person 1 + 4 |
| `evaluate_response(agent_outputs)` | `mock_agents.py` | Person 5 |
| `run_full_pipeline(query, ...)` | `mock_agents.py` | Person 1 |
| `advise_products(query, a, b, use_case)` | `product_advisory.py` | **Person 4 (real)** |

---

## 4. What the app shows

### Tab 1 — Customer Chat + Agent Console (side by side)

- **Left:** customer-facing chat window — what a shopper sees.
- **Right:** agent console showing, for the latest message:
  - detected intent + confidence
  - sentiment (Positive / Neutral / Frustrated / Angry)
  - urgency (Low / Medium / High)
  - order context (item, payment, shipment, ETA, issue history)
  - policy used (with ID, title, snippet, confidence)
  - workflow action + status + ticket ID
  - risk level + escalation team + reasons
  - evaluator score (0–100) + verdict + latency
  - internal agent trace (all 7 agents and their outputs)
  - raw audit log (JSON, collapsible)

### Tab 2 — Product Comparison

Person 4's signature feature:
- Pick a category, then two products.
- Optionally type a use case (e.g. "College", "Gaming", "Photography").
- See a spec-by-spec table including **Processor**, **RAM**, **Storage**,
  **Battery**, **Display**, **Weight**, **Warranty**, **Rating**, **Stock**.
- Get a scored recommendation with a transparent explanation.
- Out-of-stock helper: pick any product, get in-stock alternatives in the same category.

### Tab 3 — About

Explains how the mocks map to teammates' work and what to replace later.

---

## 5. Demo scenarios (pre-canned in the sidebar)

| ID | Scenario | What it proves |
|----|----------|---------------|
| S01 | Order tracking (`SE10234`) | Order Context Agent + clear ETA reply |
| S02 | Return request (`SE10235`) | Workflow Automation + policy grounding |
| S03 | Damaged headphones (`SE10236`) | Damaged-on-arrival policy + replacement ticket |
| S04 | Lost MacBook (`SE10237`) | High-value escalation to Logistics + Senior Agent |
| S05 | Coupon issue (`SE10238`) | FESTIVE10-specific policy lookup |
| S06 | Laptop comparison | Product Advisory Agent in chat mode |
| S07 | Invoice request (`SE10235`) | Workflow returns invoice availability |

Open the sidebar, pick a scenario, click the "Send scenario message" button,
and watch the right pane fill in.

---

## 6. Where to add real data later

| Today (mock) | Replace with |
|---|---|
| `data/orders.json` | Person 3's mock Order Management API output (or live CRM JSON). |
| `data/policies.json` | Person 2's curated policy KB (markdown chunks + embeddings). |
| `data/products.csv` | Person 2's catalog file or a real product API. |

The loader functions at the top of `mock_agents.py` (`load_orders`,
`load_policies`, `load_products`) are the only places that touch the
`data/` folder — point them at a different source and the rest of the app
keeps working.

Search the code for `TODO: Person X` to find every place teammates will
plug in their real implementations.

---

## 7. The demo

A line-by-line script for the final presentation lives in **`DEMO_SCRIPT.md`**.
It walks through every scenario in order with talking points and what to
emphasize on each screen.

---

## 8. Checklist mapping (from the Person 4 guide)

- [x] UI clearly shows customer input and AI response
- [x] Agent console shows each important agent output
- [x] Product comparison scenario works for the demo
- [x] Evaluator and escalation decisions are visible
- [x] Demo-friendly sample outputs across all 7 scenarios
- [x] Out-of-stock alternative recommendation flow
- [x] Audit log / agent trace for transparency
- [x] Processor / RAM / Storage / Battery / Warranty in comparison
