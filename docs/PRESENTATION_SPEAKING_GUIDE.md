# ShopEase Agentic AI — Presentation Speaking Guide

## Total Time: 15 Minutes | 5 Speakers + Live Demo

---

## SECTION 1: Opening (Ashish) — 2 minutes

### Slides 1-2: Title + Solution Overview

**Say this:**

> "Good [morning/afternoon]. We're presenting ShopEase — an Agentic AI-Powered Customer Support System.
>
> The key word is 'Agentic'. This is NOT a chatbot. It's NOT a single GPT prompt.
>
> We built 7 specialized AI agents that collaborate like a real support team — one classifies what the customer wants, another fetches their order, another checks policies, another decides if a human should take over.
>
> The difference: a chatbot hallucinates. Our system grounds every answer in verified policy data using RAG with vector embeddings. If it's not sure, it asks. If it's risky, it escalates to a human."

---

## SECTION 2: Problem (Ashish) — 1.5 minutes

### Slides 3-4: Business Problem + Why LLMs Fail

**Say this:**

> "ShopEase handles thousands of daily support queries across web, mobile, email, and social. The problems:
>
> - Customers repeat themselves — no shared context
> - Agents manually search 5+ systems to answer one question
> - Response times spike during sales events
> - Inconsistent answers — different agents quote different policies
>
> Why can't we just use ChatGPT?
>
> - It hallucinates — makes up return windows that don't exist
> - No grounding — never cites actual company policy
> - No memory — forgets the conversation after each message
> - No safety — happily promises a refund it can't give
>
> That's why we built a multi-agent system with guardrails."

---

## SECTION 3: Architecture (Ashish) — 2 minutes

### Slides 5-6: Architecture + Message Flow

**Say this:**

> "Here's our architecture. 7 agents connected through LangGraph — a state graph orchestrator from LangChain.
>
> The flow: Customer message comes in → Intent Classifier identifies what they want → Router decides which agents to call → those agents gather context → Evaluator checks quality → Risk agent decides if it's safe → Response Generator creates the answer.
>
> The key design decision: all agents share ONE state object. Nobody talks directly to another agent. They all read from and write to a shared TypedDict. This means any agent can fail without crashing the pipeline — we wrap everything in error-safe decorators.
>
> Let me hand over to the team to explain their agents."

---

## SECTION 4: Agent Deep-Dives (All Team Members) — 3 minutes

### Slide 7: Intent Classifier (Ashish — 40 seconds)

**Say this:**

> "I built the Intent Classifier. It uses GPT-4o to detect:
> - Intent (1 of 9 categories: order tracking, return, refund, product, etc.)
> - Sentiment (positive, neutral, negative, angry)
> - Urgency (low, medium, high, critical)
> - Confidence score (0-1)
>
> If confidence is below 0.4, the system asks for clarification instead of guessing wrong. In mock mode, we use priority-ordered keyword matching as fallback."

**Code to show if asked:**
```
File: src/agents/intent_classifier.py
Key: INTENT_SYSTEM_PROMPT (lines 22-55) — the GPT prompt
Key: MOCK_KEYWORD_GROUPS (lines 53-80) — priority-ordered fallback
```

---

### Slide 8: Order Context Agent (Pallavi — 40 seconds)

**Say this:**

> "I built the Order Context Agent and the entire mock data layer. When a customer mentions an order, my agent:
> 1. Extracts the order ID from the message
> 2. Calls mock APIs to fetch order status, payment, shipment tracking, CRM history
> 3. Returns a unified summary to the pipeline
>
> I created 55 customers, 140+ orders, payments, shipments, returns, and CRM history — over 12,500 lines of realistic data. Plus 7 mock API modules that simulate real backend systems."

**Code to show if asked:**
```
File: src/agents/order_context.py — the agent
File: src/integrations/mock_apis/ — 7 API modules (order, payment, logistics, CRM, etc.)
File: data/mock/ — 8 JSON files with all the data
```

---

### Slide 9: Policy Retrieval + RAG (Gunjan — 40 seconds)

**Say this:**

> "I built the Policy Knowledge Base and the retrieval system. We have 23 policies across 7 categories — returns, refunds, warranty, delivery, coupons, seller rules, and general FAQ.
>
> The key differentiator: we use RAG with vector embeddings. When a customer says 'I want my money back', we embed that query using OpenAI's text-embedding-3-small model and find the closest matching policies using cosine similarity.
>
> This means 'I want my money back' correctly matches 'Refunds are processed within 5-7 business days' — even though they share no keywords."

**Code to show if asked:**
```
File: src/knowledge/embedding_store.py — the RAG engine (embeds 23 policies, cosine similarity search)
File: src/knowledge/policies/ — 7 JSON files with all policy rules
File: src/agents/policy_retrieval.py — switches between embeddings (live) and keywords (mock)
```

---

### Product Advisory (Aditi — 30 seconds)

**Say this:**

> "I built the Product Advisory Agent and contributed to the UI design. My agent loads a 92-product catalog covering electronics, fashion, home, and more. It compares products spec-by-spec, recommends based on use case, and suggests alternatives for out-of-stock items.
>
> I also improved the mock intent classifier with priority-ordered keyword matching that correctly distinguishes 'damaged' from 'delivery complaint' from 'order tracking'."

**Code to show if asked:**
```
File: src/agents/product_advisory.py — loads from catalog.json, compares specs
File: src/knowledge/products/catalog.json — 92 products with full specs
```

---

### Escalation & Risk (Rohan — 40 seconds)

**Say this:**

> "I built the Risk and Escalation system. It's not a simple if/else — it's a multi-factor weighted scoring engine with 6 factors:
> - Sentiment (angry = high risk)
> - Order value (over Rs 10,000 = elevated)
> - Classification confidence (low = uncertain = escalate)
> - Customer tier (VIP gets faster attention)
> - Repeated contact history
> - Issue severity
>
> Based on the score, the system decides: auto-respond, queue for human approval (HITL), or escalate directly. I also built the audit log system — every interaction is traced."

**Code to show if asked:**
```
File: src/agents/escalation_risk.py — 536 lines, multi-factor scoring
File: src/governance/approval_queue.py — HITL queue with SLA tracking
File: src/governance/audit.py — durable audit trail
```

---

## SECTION 5: LIVE DEMO (Ashish) — 3 minutes

### Switch to browser: http://localhost:8501

**Demo 1: Order Tracking (45 seconds)**

- Select customer: Rahul Patel (Premium) - CUST_1001
- Select scenario: "Order Tracking" → Click Send
- Point out:
  - "See the natural response with actual tracking number, carrier name, ETA"
  - Show Agent Console: "Intent: order_tracking, 100% confidence, Risk: 0.30, Band: auto"
  - Expand "Order Context" toggle: "Real customer data — name, tier, order amount"

**Demo 2: Damaged Product Escalation (45 seconds)**

- Reset chat
- Select customer: Vikram Singh (VIP) - CUST_1003
- Select scenario: "Damaged Product" → Click Send
- Point out:
  - "System detected angry sentiment, high-value order → ESCALATED"
  - "Notice it asks for photos — proactive evidence collection"
  - Click "HITL Queue" tab: "Here's what the human reviewer sees — they can Approve, Reject, or Escalate further"
  - Click "Approve"

**Demo 3: RAG + Analytics (45 seconds)**

- Go back to Chat tab, type: "I want my money back"
- Show Agent Console → expand "Policy (RAG Embeddings)"
  - "See: these policies were found using SEMANTIC SEARCH, not keywords. 'Money back' matched 'refund processing timeline'"
- Click "Analytics" tab
  - "Real-time metrics: 3 queries, 2 resolved by AI, 1 escalated, 67% resolution rate"

**Demo 4: Quick Actions (30 seconds)**

- Point out the "Request callback" button below chat
- Click it
- "See: the customer clicked 'Request callback' → system sends escalation message → goes to HITL queue"

---

## SECTION 6: Code Walkthrough (Ashish) — 2 minutes

### Show in Cursor/VS Code:

**File 1: `src/orchestrator/graph.py` (30 seconds)**

> "This is the heart of the system. LangGraph StateGraph definition. Every agent is a node. Conditional edges decide the path based on intent and risk. Error-safe wrappers mean no agent crash kills the pipeline."

Point to:
- `graph.add_node("classify_intent", safe_classify_intent)` — agents as nodes
- `graph.add_conditional_edges("classify_intent", route_after_intent, {...})` — routing logic
- `error_safe` decorator — catches exceptions gracefully

**File 2: `src/knowledge/embedding_store.py` (30 seconds)**

> "Our RAG implementation. 23 policies embedded at startup using OpenAI text-embedding-3-small. Customer query gets embedded, then cosine similarity finds the nearest matches. Top 3 returned."

Point to:
- `self.embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")`
- `_cosine_similarity()` — the math
- `store.search(query, intent, top_k=3)`

**File 3: Run tests live (60 seconds)**

> "Let me show you our test suite."

Run in terminal:
```
python tests/test_resilience.py
```

> "10 tests, all passing. This covers: happy path, missing data, escalation, garbage input, low confidence. The system never crashes."

---

## SECTION 7: Future Enhancements (Ashish) — 1 minute

### Slide 10

**Say this:**

> "The architecture is designed for production scale:
>
> Short-term: voice input, Hindi support, customer satisfaction scoring.
>
> Medium-term: swap JSON for Azure Cosmos DB, use Azure AI Search for enterprise RAG, Redis for session caching. The beautiful thing — all agent function signatures stay the same. Zero code change.
>
> Long-term: proactive outreach — notify customers before they complain. Self-learning from resolved tickets. Multi-modal — image analysis for damage claims. Integration with Salesforce and SAP.
>
> The system is built to grow."

---

## SECTION 8: Q&A — 2 minutes

### Likely Questions and Answers:

**Q: "How is this different from just using ChatGPT?"**

> "Three things: First, grounding — every answer cites a verified policy reference. ChatGPT makes things up. Second, safety — risky cases go to humans, not auto-answered. Third, real data — we fetch actual order status, not generate fictional ones."

**Q: "How do you prevent hallucination?"**

> "RAG with embeddings ensures the response generator only uses verified policy text. The evaluator checks: is there a policy citation? If not, quality score drops and the system asks for more info instead of guessing."

**Q: "Can this handle real traffic?"**

> "The architecture is infrastructure-agnostic. Replace JSON with Cosmos DB, swap mock APIs with real ones — same function signatures, same agents, same graph. We documented the full migration path."

**Q: "What about data privacy?"**

> "HITL approval for sensitive actions. PII masking utilities built in. Audit trail for every interaction. Azure OpenAI Service provides data residency when deployed."

**Q: "How do you measure success?"**

> "Our evaluation harness runs 25+ test cases measuring: intent accuracy, escalation precision, response groundedness, and latency. Current results: 100% intent accuracy with GPT-4o, <3s response time, 100% policy grounding."

---

## Tech Stack Summary (for reference)

| Layer | Technology | Why We Chose It |
|-------|-----------|-----------------|
| Orchestration | LangGraph | Graph-based multi-agent with conditional edges, shared state |
| LLM | OpenAI GPT-4o | Best classification + generation quality |
| Embeddings | text-embedding-3-small | Fast, cheap, good semantic similarity |
| RAG | Custom cosine similarity | Simple, no external DB dependency for prototype |
| Frontend | Streamlit | Rapid prototyping, 4 tabs, interactive demo |
| Data | JSON mock (55 customers, 140+ orders) | Fast iteration, documented Azure scale path |
| CI/CD | GitHub Actions | Auto-test on every push |
| Testing | pytest + custom harness | 35+ test cases across 4 test suites |

---

## Key Code Blocks to Highlight

### 1. The Orchestration Graph (`src/orchestrator/graph.py`)
```python
graph = StateGraph(AgentState)
graph.add_node("classify_intent", safe_classify_intent)
graph.add_node("fetch_order", safe_fetch_order)
graph.add_conditional_edges("classify_intent", route_after_intent, {
    "fetch_order": "fetch_order",
    "retrieve_policy": "retrieve_policy",
    "advise_product": "advise_product",
    "direct_response": "evaluate",
    "clarify": "clarify",
})
```
**Explain:** "Each agent is a node. The router function decides the next step based on intent and data availability."

### 2. RAG Embedding Search (`src/knowledge/embedding_store.py`)
```python
query_embedding = self.embeddings_model.embed_query(query_text)
for i, policy_emb in enumerate(self.policy_embeddings):
    similarity = _cosine_similarity(query_embedding, policy_emb)
    scores.append((similarity, i))
scores.sort(key=lambda x: x[0], reverse=True)
```
**Explain:** "Embed the customer query, compare against all 23 policy embeddings, return the closest 3."

### 3. Error-Safe Wrapper (`src/orchestrator/graph.py`)
```python
def error_safe(agent_name: str):
    def decorator(func):
        def wrapper(state):
            try:
                return func(state)
            except Exception as e:
                return {"agents_called": [f"{agent_name}(ERROR)"], "audit_trail": [...]}
        return wrapper
    return decorator
```
**Explain:** "Any agent can fail — the pipeline continues. The evaluator detects the error and adjusts quality."

### 4. Multi-Factor Risk Scoring (`src/agents/escalation_risk.py`)
```python
WEIGHTS = {
    "sentiment": 0.25,
    "order_value": 0.20,
    "intent_confidence": 0.15,
    "customer_tier": 0.10,
    "repeated_contact": 0.15,
    "issue_severity": 0.15,
}
```
**Explain:** "Not a simple if/else. Weighted scoring across 6 dimensions. Severity 80+ forces escalation regardless of score."

### 5. Conversation Memory (in `app.py`)
```python
history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
state = build_initial_state(message=message, conversation_history=history)
```
**Explain:** "Every new message includes the full conversation history. GPT uses it to maintain context — 'my order' in message 2 refers to the order discussed in message 1."

---

## Speaking Order Summary

| Order | Person | Section | Time |
|-------|--------|---------|------|
| 1 | Ashish | Opening + Problem + Architecture | 5.5 min |
| 2 | Pallavi | Order Context Agent | 40 sec |
| 3 | Gunjan | Policy Retrieval + RAG | 40 sec |
| 4 | Aditi | Product Advisory + UI | 30 sec |
| 5 | Rohan | Risk + Escalation + HITL | 40 sec |
| 6 | Ashish | Live Demo | 3 min |
| 7 | Ashish | Code Walkthrough | 2 min |
| 8 | Ashish | Future + Close | 1 min |
| 9 | All | Q&A | 2 min |
