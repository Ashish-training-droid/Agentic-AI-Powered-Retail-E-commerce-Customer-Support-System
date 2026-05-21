# Aditi (Person 4): Product Advisory + UI/UX Engineer

## Your Role

You own the **customer-facing experience** — the chat UI, agent-assist console, and the Product Advisory Agent that helps shoppers compare and choose products.

## What You Need to Build

### 1. Product Advisory Agent (Week 2-3)

**Your main code file:** `src/agents/product_advisory.py`

Replace the mock implementation with real product comparison logic.

**What it should do:**

```python
def advise_product(state: AgentState) -> AgentState:
    # 1. Parse product names, categories, or needs from message
    # 2. Search product catalog (from Gunjan (Person 2)'s catalog.json)
    # 3. Compare specs side-by-side
    # 4. Check inventory availability (from Pallavi (Person 3)'s APIs)
    # 5. Suggest alternatives for out-of-stock items
    # 6. Generate recommendation based on stated needs
```

**Capabilities to build:**
- Compare 2-3 products by specs
- Recommend based on use case ("laptop for college", "headphones for travel")
- Show price bands and value-for-money
- Suggest alternatives when a product is out of stock
- Handle compatibility questions ("will this case fit my phone?")

**Output format:**

```python
{
    "product_context": {
        "comparison": [
            {
                "name": "HP Pavilion 15",
                "price": 55999,
                "specs": {"ram": "16GB", ...},
                "rating": 4.3,
                "best_for": "college students",
                "in_stock": True
            },
            ...
        ],
        "recommendation": "For your needs, we recommend...",
        "alternatives": [...]
    },
    "agents_called": ["product_advisory"],
    "audit_trail": [...]
}
```

### 2. Customer Chat UI (Week 3-4)

Build a simple chat interface in `src/ui/customer_chat/`.

**Recommended: Streamlit** (fast to prototype)

```
src/ui/customer_chat/
├── app.py              # Main Streamlit app
├── components.py       # Reusable UI components
└── styles.css          # Custom styling (optional)
```

**Features required:**
- Chat input box for customer messages
- Chat history display (customer messages + AI responses)
- Show "typing..." indicator while pipeline runs
- Display response with confidence badge (green > 0.8, yellow > 0.6, red < 0.6)
- Show cited policy references as expandable footnotes
- Show suggested next action as a clickable chip
- Channel selector (web/mobile/email simulation)

**Basic Streamlit structure:**

```python
import streamlit as st
from src.orchestrator.graph import app
from src.utils.session import build_initial_state, generate_session_id

st.title("ShopEase Support Assistant")

if "session_id" not in st.session_state:
    st.session_state.session_id = generate_session_id()
    st.session_state.history = []

# Chat input
user_message = st.chat_input("How can we help you today?")

if user_message:
    # Build state and run pipeline
    state = build_initial_state(
        message=user_message,
        customer_id=st.session_state.get("customer_id", "CUST_1001"),
        channel="web",
        session_id=st.session_state.session_id,
    )
    result = app.invoke(state)
    
    # Display response
    st.chat_message("assistant").write(result["response_text"])
```

### 3. Agent-Assist Console (Week 3-4)

Build an internal dashboard in `src/ui/agent_console/`:

```
src/ui/agent_console/
├── app.py              # Main Streamlit app (separate from customer chat)
└── components.py       # Dashboard widgets
```

**What support agents see:**
- Customer summary (name, tier, recent orders)
- Current conversation with AI analysis overlay
- Intent + sentiment + urgency badges
- Order context panel (order details, payment, shipment)
- Policy references used (with full rule text)
- Suggested response (editable by agent)
- Confidence score with explanation
- Escalation reason (if escalated)
- One-click actions: "Approve response", "Edit & send", "Escalate manually"
- Audit trail showing which agents were called

**Layout suggestion:**

```
+------------------+-------------------+------------------+
|  Customer Info   |   Conversation    |  Context Panel   |
|  - Name, tier    |   - Chat history  |  - Order details |
|  - Past tickets  |   - AI analysis   |  - Policy refs   |
|  - Order history |                   |  - Risk score    |
+------------------+-------------------+------------------+
|              Suggested Response + Actions               |
|  [Approve & Send]  [Edit]  [Escalate]  [Add Note]     |
+---------------------------------------------------------+
```

### 4. Response Generation (Shared with Ashish (Person 1)) (Week 3-4)

You share ownership of `src/agents/response_generator.py` with Ashish (Person 1). Your focus:

- **Tone adaptation:** Different tone for web chat vs email vs social
- **Formatting:** Bullet points for comparisons, short sentences for chat
- **Product-specific responses:** Rich product cards with specs and images references

### 5. Demo Screenshots & Script (Week 5-6)

Prepare for the final presentation:
- Screenshot every key UI screen
- Write a demo script with exact messages to type
- Record a backup video in case live demo fails

## How to Test Your Work

```bash
# Test product advisory
python -m src.main --demo 3   # Product comparison (laptop)

# Run customer chat UI
streamlit run src/ui/customer_chat/app.py

# Run agent console
streamlit run src/ui/agent_console/app.py
```

## Dependencies to Add

Add these to `requirements.txt`:
```
streamlit>=1.35.0
```

## Handoff Partners

- **Ashish (Person 1) (you report to):** Your UI displays the pipeline output; shared Response Generator
- **Gunjan (Person 2) (provides data):** Product catalog and FAQ for your advisory agent
- **Pallavi (Person 3) (provides APIs):** Inventory check for stock availability in product recommendations

## Quality Checklist

- [ ] Product advisory can compare at least 3 product categories (electronics, fashion, accessories)
- [ ] Comparison includes specs, price, rating, and stock status
- [ ] Customer chat shows full conversation with response metadata
- [ ] Agent console displays all pipeline outputs clearly
- [ ] UI handles errors gracefully (shows friendly message, not stack trace)
- [ ] Demo script covers all 7 sample conversations
- [ ] Screenshots captured for every major screen
- [ ] Product recommendations include "best for" reasoning
