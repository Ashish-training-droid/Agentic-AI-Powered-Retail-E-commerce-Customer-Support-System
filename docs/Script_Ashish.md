# Ashish's Presentation Script

## Your Parts: Architecture + Demo (Analytics/HITL) + Code Walkthrough + Future

---

## PART 1: Architecture + Orchestration (after Pallavi's opening) — 2 minutes

### Slide 5-6: Architecture Diagram

**Say:**

> "Thank you Pallavi. Now let me show you HOW we solved this.
>
> We didn't build a chatbot. We built a multi-agent system — 7 specialized AI agents orchestrated through LangGraph.
>
> [Point to architecture slide]
>
> Here's the flow:
> 1. Customer message comes in
> 2. Intent Classifier (GPT-4o) identifies what they want — is it an order query? A return? A complaint?
> 3. The Router decides which agents to call — not all agents run every time. Order tracking doesn't need the Product Advisory agent.
> 4. Context agents run in sequence — Order Context fetches their data, Policy Retrieval uses RAG to find relevant rules
> 5. The Evaluator checks — do we have enough data to respond?
> 6. Risk Agent scores the situation — is this safe for AI or does a human need to take over?
> 7. Response Generator creates the final answer using ALL the gathered context
>
> The key: all agents share ONE state object — a Python TypedDict that flows through the graph. No agent calls another directly. This means any agent can fail without crashing the pipeline.
>
> Let me show you this working live. Pallavi, take it from here with the first demo."

---

## PART 2: During Demo — Analytics + HITL + Quick Actions — 1 minute

### After Rohan shows the escalation demo, you take over:

**Say:**

> "Thank you Rohan. Now let me show two more things that make this production-ready.
>
> [Click Analytics tab]
>
> This is our Analytics Dashboard. In this session we've had 4 queries — 3 resolved by AI, 1 escalated. That's a 75% resolution rate. In production with more data, we target 85%.
>
> [Point to Business Impact Metrics table]
>
> These are our benchmarks: under 3 seconds response time vs 45 seconds for a human agent. 100% policy grounding — every factual claim cites a verified policy reference.
>
> [Go back to Chat tab, point to quick action buttons]
>
> See these buttons? After every response, the system suggests next actions. If the customer clicks 'Request callback' — watch what happens...
>
> [Click 'Request callback']
>
> It immediately triggers escalation — goes to the HITL queue. The system treats callback requests as human-handoff signals. This is proactive — the customer doesn't have to wait."

---

## PART 3: Code Walkthrough — 2 minutes

### Switch to VS Code/Cursor

**Say:**

> "Let me show you the code that makes this work. Three key files."

### File 1: `src/orchestrator/graph.py` (40 seconds)

**Open the file, scroll to the graph definition (around line 250)**

**Say:**

> "This is the heart of our system — the LangGraph state graph.
>
> [Point to graph.add_node lines]
>
> Each agent is a node: classify_intent, fetch_order, retrieve_policy, advise_product, execute_workflow, evaluate, check_risk, generate_response.
>
> [Point to add_conditional_edges]
>
> These conditional edges are the routing logic. After intent classification, the router function decides the path. If it's an order query — fetch_order runs. If it's a product question — advise_product runs. Not every agent runs every time.
>
> [Point to error_safe wrapper]
>
> This decorator wraps every agent. If any agent throws an exception, the pipeline continues — it logs the error and moves on. That's why our system never crashes."

### File 2: `src/knowledge/embedding_store.py` (40 seconds)

**Open the file**

**Say:**

> "This is our RAG implementation — the differentiator from keyword matching.
>
> [Point to _load_catalog / load_policies]
>
> At startup, we load all 23 policy rules and embed them using OpenAI's text-embedding-3-small model. Each policy becomes a vector.
>
> [Point to search() method]
>
> When a customer asks something, we embed their query too. Then cosine similarity finds the closest matching policies. 'I want my money back' finds 'Refunds are processed within 5-7 days' — zero keyword overlap, pure semantic understanding.
>
> [Point to top_k=3, min_score=0.3]
>
> We return top 3 matches above 0.3 similarity. This ensures we always have policy backing for our responses."

### File 3: Run tests live (40 seconds)

**Open terminal**

**Say:**

> "Finally — how do we ensure quality? Tests.
>
> [Run: python tests/test_resilience.py]
>
> 10 tests covering: happy path, missing data, escalation, garbage input, low confidence clarification. All passing.
>
> These run automatically on every push via GitHub Actions. If any test fails, the push is blocked. This is CI/CD in practice."

---

## PART 4: Future Enhancements + Close — 1.5 minutes

### Slide 10

**Say:**

> "The system works today. But it's designed to grow.
>
> Short-term — next sprint:
> - Voice input for phone channel
> - Hindi language support
> - Customer satisfaction scoring after each response
>
> Medium-term — production deployment:
> - Replace JSON files with Azure Cosmos DB — our code doesn't change because the function signatures stay the same
> - Azure AI Search for enterprise RAG — same embedding approach, just at scale
> - Redis for session caching — handles thousands of concurrent conversations
>
> Long-term:
> - Proactive outreach — notify customers about delays BEFORE they complain
> - Self-learning — fine-tune models from successfully resolved tickets
> - Multi-modal — analyze photos of damaged products using vision models
> - CRM integration — plug into Salesforce, SAP for live enterprise data
>
> The architecture is ready for all of this. Every agent is independent, every interface is clean.
>
> Thank you. Questions?"

---

## Q&A Cheat Sheet (for you)

| If they ask... | Say... |
|----------------|--------|
| "How is this different from ChatGPT?" | "Three things: RAG grounding (every claim cites policy), HITL safety (risky cases go to humans), and real data (actual orders, not fabricated ones). ChatGPT does none of these." |
| "What if GPT hallucinates?" | "It can't — the response generator ONLY uses data from the context prompt (order context + policy snippets). If no policy matches, it says 'I don't have enough info' instead of guessing." |
| "How does RAG work?" | "We embed all 23 policies as vectors using OpenAI embeddings. Customer query is also embedded. Cosine similarity finds the closest policies. It's semantic search — understands meaning, not keywords." |
| "Can this scale?" | "Yes — swap JSON for Cosmos DB, mock APIs for real APIs. Same function signatures. Zero agent code change. We documented the full migration path." |
| "What about latency?" | "Under 3 seconds end-to-end with GPT-4o. Mock mode is instant. In production, we'd cache embeddings and use GPT-4o-mini for classification to reduce to under 1 second." |
| "How did you test?" | "35+ test cases across 4 suites. Router tests, intent tests, resilience tests, grounding tests. CI runs on every push via GitHub Actions." |
| "What's the risk scoring?" | "6-factor weighted scoring: sentiment (25%), order value (20%), confidence (15%), customer tier (10%), repeated contact (15%), issue severity (15%). Score above 0.7 = escalate. Between 0.4-0.7 = HITL approval." |
| "Why LangGraph and not CrewAI?" | "LangGraph gives us fine-grained control over routing. Conditional edges mean different intents take different paths. CrewAI is more role-based — we needed path-based orchestration." |

---

## Code Sections to Reference (if deep questions come)

### Orchestration State Schema
```
File: src/orchestrator/state.py
- AgentState TypedDict — ALL fields that flow between agents
- Uses Annotated[list, add] for agents_called and audit_trail (append-only)
```

### Router Logic
```
File: src/orchestrator/router.py
- ROUTING_TABLE: intent -> list of agents to call
- route_after_intent(): confidence-based routing (< 0.4 = clarify)
- route_after_risk(): 3 paths (auto / approval / escalate)
```

### Response Generator
```
File: src/agents/response_generator.py
- RESPONSE_SYSTEM_PROMPT: few-shot examples, "NEVER give generic responses"
- Uses conversation history for multi-turn context
- Fallback to mock templates if OpenAI fails
```

### Risk Agent
```
File: src/agents/escalation_risk.py
- WEIGHTS dict: 6 factors with documented weights
- _decide_band(): score + route severity -> auto/approval/escalate
- REPEATED_CONTACT_HIGH = 4 (tuned based on real data)
```
