# ShopEase Agentic AI — Aditi (Person 4) Module

Customer chat UI, agent-assist console, and Product Advisory Agent for the
ShopEase Retail & E-commerce Customer Support Capstone Project.

This module is built and owned by **Aditi (Person 4)** (UI / UX + Product Advisory).
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
│   ├── product_advisory.py         # Aditi (Person 4)'s signature Product Advisory Agent
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
| `classify_intent(query)` | `mock_agents.py` | Ashish (Person 1) |
| `get_order_context(order_id, query)` | `mock_agents.py` | Pallavi (Person 3) |
| `retrieve_policy(intent, query)` | `mock_agents.py` | Gunjan (Person 2) |
| `automate_workflow(intent, order_ctx)` | `mock_agents.py` | Pallavi (Person 3) |
| `assess_risk(query, intent_out, order_ctx)` | `mock_agents.py` | Rohan (Person 5) |
| `generate_response(query, agent_outputs)` | `mock_agents.py` | Ashish (Person 1) + 4 |
| `evaluate_response(agent_outputs)` | `mock_agents.py` | Rohan (Person 5) |
| `run_full_pipeline(query, ...)` | `mock_agents.py` | Ashish (Person 1) |
| `advise_products(query, a, b, use_case)` | `product_advisory.py` | **Aditi (Person 4) (real)** |

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

Aditi (Person 4)'s signature feature:
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
| `data/orders.json` | Pallavi (Person 3)'s mock Order Management API output (or live CRM JSON). |
| `data/policies.json` | Gunjan (Person 2)'s curated policy KB (markdown chunks + embeddings). |
| `data/products.csv` | Gunjan (Person 2)'s catalog file or a real product API. |

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

## 8. Checklist mapping (from the Aditi (Person 4) guide)

- [x] UI clearly shows customer input and AI response
- [x] Agent console shows each important agent output
- [x] Product comparison scenario works for the demo
- [x] Evaluator and escalation decisions are visible
- [x] Demo-friendly sample outputs across all 7 scenarios
- [x] Out-of-stock alternative recommendation flow
- [x] Audit log / agent trace for transparency
- [x] Processor / RAM / Storage / Battery / Warranty in comparison
# ShopEase: Agentic AI-Powered Retail & E-commerce Customer Support System

## Overview

An intelligent, multi-agent AI system designed to transform customer support for **ShopEase Retail & Marketplace** — a fast-growing e-commerce company selling electronics, fashion, home goods, groceries, and lifestyle products across web, mobile, and physical stores.

The system uses specialized AI agents that collaborate to resolve customer issues: classifying intent, retrieving order context, interpreting policies, automating workflows, generating safe responses, and escalating complex cases to human teams.

## Business Problem

ShopEase handles thousands of daily customer interactions across chat, email, phone, and social channels. During promotions and festive sales, the support team struggles with:

- **Fragmented context** — customers repeat information across channels while agents manually search multiple systems
- **Slow resolution** — longer response times during peak traffic events
- **Inconsistent answers** — different agents give different policy guidance
- **High operational cost** — manual ticket handling and repeated escalations
- **Revenue leakage** — unresolved payment, refund, coupon, and return issues
- **Customer churn** — slow post-purchase support erodes loyalty

## Proposed Solution

A multi-agent orchestration system that:

1. Understands customer intent, urgency, and sentiment from natural language
2. Retrieves trusted information from order systems, product catalogs, and policy documents
3. Guides customers through self-service workflows (returns, refunds, invoices, etc.)
4. Provides support agents with summarized context, recommended responses, and next-best actions
5. Escalates sensitive cases (fraud, payment disputes, damaged high-value items) to the right human team
6. Maintains audit logs, confidence scores, and policy references for transparency

## High-Level Architecture

```mermaid
flowchart TD
    subgraph channels [Customer Channels]
        Web[Website Chat]
        Mobile[Mobile App]
        Email[Email]
        Social[Social Media]
    end

    subgraph ui [User Interfaces]
        CustomerChat[Customer Chat UI]
        AgentConsole[Agent Assist Console]
    end

    subgraph orchestration [Orchestration Layer]
        Router[Intent Router / Controller]
        StateManager[State Manager]
    end

    subgraph agents [AI Agent Layer]
        IntentAgent[Intent Classification Agent]
        OrderAgent[Order Context Agent]
        PolicyAgent[Policy Retrieval Agent]
        ProductAgent[Product Advisory Agent]
        WorkflowAgent[Workflow Automation Agent]
        RiskAgent[Escalation and Risk Agent]
        ResponseAgent[Response Generation Agent]
    end

    subgraph knowledge [Knowledge Layer]
        PolicyKB[Policy KB]
        ProductCatalog[Product Catalog]
        FAQ[FAQ Repository]
    end

    subgraph integrations [Mock Integration Layer]
        OrderAPI[Order Management API]
        PaymentAPI[Payment API]
        LogisticsAPI[Logistics API]
        InventoryAPI[Inventory API]
        CRMAPI[CRM API]
        TicketAPI[Ticketing API]
    end

    subgraph governance [Governance Layer]
        AuditLog[Audit Logs]
        AccessControl[Access Control]
        HumanApproval[Human Approval Gate]
    end

    channels --> ui
    ui --> Router
    Router --> IntentAgent
    IntentAgent --> StateManager
    StateManager --> OrderAgent
    StateManager --> PolicyAgent
    StateManager --> ProductAgent
    StateManager --> WorkflowAgent
    StateManager --> RiskAgent
    OrderAgent --> integrations
    PolicyAgent --> knowledge
    ProductAgent --> knowledge
    WorkflowAgent --> integrations
    RiskAgent --> ResponseAgent
    ResponseAgent --> ui
    ResponseAgent --> governance
```

## Agent Roles

| Agent | Responsibility | Owner |
|-------|---------------|-------|
| **Intent Classification** | Identify customer goal, urgency, sentiment, and issue category | Ashish (Person 1) |
| **Order Context** | Retrieve order, shipment, payment, invoice, return, and CRM history | Pallavi (Person 3) |
| **Policy Retrieval** | Search approved return, refund, warranty, delivery, and coupon policies | Gunjan (Person 2) |
| **Product Advisory** | Compare products, check compatibility, suggest alternatives | Aditi (Person 4) |
| **Workflow Automation** | Initiate self-service actions (return, refund, invoice, ticket) | Pallavi (Person 3) |
| **Escalation & Risk** | Detect high-risk, low-confidence, or sensitive cases and route to humans | Rohan (Person 5) |
| **Response Generation** | Create grounded, brand-aligned customer responses | Ashish (Person 1) + Aditi (Person 4) |

## Orchestration Flow

```mermaid
sequenceDiagram
    participant C as Customer
    participant R as Router
    participant IC as Intent Classifier
    participant OC as Order Context
    participant PR as Policy Retrieval
    participant WF as Workflow Agent
    participant ER as Escalation/Risk
    participant RG as Response Generator

    C->>R: Send message
    R->>IC: Classify intent & sentiment
    IC->>R: Intent, urgency, confidence

    alt Order-related intent
        R->>OC: Fetch order context
        OC->>R: Order summary
    end

    alt Policy-related intent
        R->>PR: Retrieve policy
        PR->>R: Policy snippet + reference
    end

    alt Action needed
        R->>WF: Execute workflow
        WF->>R: Action result
    end

    R->>ER: Check risk & escalation
    ER->>R: Risk score + routing decision

    alt No escalation needed
        R->>RG: Generate response
        RG->>C: Final answer with confidence
    else Escalation required
        ER->>R: Route to human team
    end
```

## Sample Use Cases

1. **Order Tracking** — "Where is my order?" retrieves shipment status and provides updated delivery estimate
2. **Return Request** — checks eligibility, explains conditions, initiates return workflow
3. **Product Comparison** — compares laptop specs for a college student and suggests best option
4. **Damaged Product** — collects evidence, verifies policy, escalates to replacement team
5. **Coupon Issue** — checks coupon terms, cart eligibility, explains why it wasn't applied
6. **Agent Assist** — summarizes order history, previous contacts, and recommends next action
7. **Lost Shipment** — flags as high priority, routes to logistics and fraud review

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| LLM Framework | LangChain / LangGraph |
| Vector Store | FAISS / ChromaDB (for RAG) |
| Backend API | FastAPI |
| Frontend | Streamlit / Gradio (prototype) |
| Data | JSON mock APIs, CSV datasets |
| Testing | pytest |
| Version Control | Git + GitHub |

## What is Where — Project Map

| File / Folder | What It Does | Owner |
|---------------|-------------|-------|
| **`src/orchestrator/graph.py`** | The main LangGraph workflow — connects all agents into a pipeline | Ashish (Person 1) |
| **`src/orchestrator/state.py`** | Shared state schema (TypedDict) that flows between all agents | Ashish (Person 1) |
| **`src/orchestrator/router.py`** | Routing logic — decides which agents to call based on intent | Ashish (Person 1) |
| **`src/orchestrator/evaluator.py`** | Quality gate — checks confidence and completeness before responding | Ashish (Person 1) |
| **`src/agents/intent_classifier.py`** | Classifies customer intent, sentiment, urgency using OpenAI | Ashish (Person 1) |
| **`src/agents/response_generator.py`** | Generates grounded, policy-cited customer responses | Ashish (Person 1) + 4 |
| **`src/agents/order_context.py`** | Retrieves order/payment/shipment data for the customer | Pallavi (Person 3) |
| **`src/agents/policy_retrieval.py`** | Searches policy KB and returns relevant rules with citations | Gunjan (Person 2) |
| **`src/agents/product_advisory.py`** | Compares products, suggests alternatives, checks stock | Aditi (Person 4) |
| **`src/agents/workflow_automation.py`** | Executes actions: return, refund check, ticket creation | Pallavi (Person 3) |
| **`src/agents/escalation_risk.py`** | Risk scoring and escalation routing to human teams | Rohan (Person 5) |
| **`src/utils/`** | Helper functions: logging, validation, formatting, retry, metrics | Shared |
| **`src/config.py`** | API keys, model config, confidence thresholds | Ashish (Person 1) |
| **`src/main.py`** | Demo runner — runs sample conversations through the full pipeline | Ashish (Person 1) |
| **`src/knowledge/`** | Policy documents, product catalog, FAQs (knowledge base) | Gunjan (Person 2) |
| **`src/integrations/mock_apis/`** | Mock backend APIs (orders, payments, logistics, CRM) | Pallavi (Person 3) |
| **`src/ui/customer_chat/`** | Customer-facing chat interface (Streamlit) | Aditi (Person 4) |
| **`src/ui/agent_console/`** | Internal agent-assist dashboard | Aditi (Person 4) |
| **`src/governance/`** | Audit logs, access control, human approval gates | Rohan (Person 5) |
| **`data/mock/`** | Sample orders, customers, and demo conversations | Pallavi (Person 3) |
| **`tests/`** | Evaluation suite, test cases, metrics | Rohan (Person 5) |
| **`docs/architecture.md`** | Full system architecture with agent contracts and state schema | Ashish (Person 1) |
| **`docs/team_guides/`** | Detailed step-by-step guides for each team member | Ashish (Person 1) |
| **`CONTRIBUTING.md`** | How to clone, setup, and start contributing | Ashish (Person 1) |

## How It All Connects

```
Customer sends message
       │
       ▼
 Intent Classifier ──→ "What do they want? How do they feel?"
       │
       ▼
 Router decides ──→ "Which agents do I need for this intent?"
       │
  ┌────┼────┬────────────┐
  ▼    ▼    ▼            ▼
Order Policy Product  Workflow    ← teammates build these
  │    │    │            │
  └────┼────┴────────────┘
       │
       ▼
 Evaluator ──→ "Do we have enough info? Is quality OK?"
       │
       ▼
 Risk Check ──→ "Safe to answer? Or escalate to human?"
       │
  ┌────┴────┐
  ▼         ▼
Response  Escalation
  │         │
  ▼         ▼
Customer gets answer or specialist takes over
```

## Team Roles

| Person | Role | Primary Ownership |
|--------|------|-------------------|
| Ashish (Person 1) | Project Help + Orchestration Architect | Architecture, agent router, state schema, integration |
| Gunjan (Person 2) | Knowledge Base + Policy Retrieval Engineer | Policy KB, FAQ, product catalog, RAG retrieval |
| Pallavi (Person 3) | Mock API + Workflow Automation Engineer | Mock APIs, order context agent, workflow automation |
| Aditi (Person 4) | Product Advisory + UI/UX Engineer | Customer chat UI, agent console, product advisory agent |
| Rohan (Person 5) | Escalation, QA, Evaluation + Presentation Lead | Risk agent, audit logs, testing, metrics, final deck |

## 6-Day Execution Timeline

| Day | Theme | Key Output | Who Drives |
|-----|-------|-----------|-----------|
| Day 1 | Scope + Design | Use cases, architecture, mock data schema, repo setup | Ashish (Person 1) |
| Day 2 | Data + Agent Skeletons | KB, mock APIs, intent/order/policy agents running | Gunjan (Person 2) + 3 |
| Day 3 | Core Agents | All 7 agents with real logic, integrated flows | All |
| Day 4 | UI + Integration | Customer chat + agent console + audit logs | Aditi (Person 4) + 5 |
| Day 5 | Evaluation + Fixes | Test report, metrics, refined flows, bug fixes | Rohan (Person 5) + All |
| Day 6 | Final Packaging | Presentation, demo script, final report | Rohan (Person 5) leads |

## Getting Started

### Prerequisites

- Python 3.12+
- Git

### Setup

```bash
git clone https://github.com/Ashish-training-droid/Agentic-AI-Powered-Retail-E-commerce-Customer-Support-System.git
cd Agentic-AI-Powered-Retail-E-commerce-Customer-Support-System
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### Running the Demo

```bash
# Run all 7 demo conversations (works in mock mode, no API key needed)
set USE_MOCK=true
python -m src.main

# Run a specific demo scenario (1-7)
python -m src.main --demo 1    # Order tracking
python -m src.main --demo 2    # Return request
python -m src.main --demo 3    # Product comparison
python -m src.main --demo 4    # Damaged product (escalation)
python -m src.main --demo 5    # Coupon issue
python -m src.main --demo 6    # Refund status
python -m src.main --demo 7    # General FAQ
```

## Source Code Reference — File-by-File Guide

### Entry Point

| File | Purpose |
|------|---------|
| `src/main.py` | **Demo runner** — loads sample conversations from `data/mock/sample_conversations.json`, feeds each message through the full LangGraph pipeline, and prints step-by-step results (intent, order context, policy, workflow action, quality score, risk assessment, and final response). Supports running all 7 demos or a single one via `--demo N`. |

### Configuration

| File | Purpose |
|------|---------|
| `src/config.py` | **Central configuration** — loads environment variables (`OPENAI_API_KEY`, `OPENAI_MODEL`, `USE_MOCK`), defines confidence thresholds for routing/evaluation/response serving, and lists all supported intents, sentiments, urgency levels, and channels used across the system. |

### Orchestration Layer (`src/orchestrator/`)

| File | Purpose |
|------|---------|
| `src/orchestrator/state.py` | **Shared state schema** — defines the `AgentState` TypedDict that flows through the entire pipeline. Every field an agent reads or writes is declared here (input fields, intent output, order context, policy snippets, product context, workflow results, risk scores, response text, quality scores, and audit trail). |
| `src/orchestrator/graph.py` | **LangGraph workflow builder** — constructs and compiles the state graph connecting all agent nodes. Wraps every agent with an `error_safe` decorator so a single agent failure never crashes the pipeline. Defines the clarification node (low confidence) and escalation node (high risk). Wires the full flow: `START → classify_intent → [route] → context agents → evaluate → check_risk → generate_response / escalate → END`. |
| `src/orchestrator/router.py` | **Routing logic** — the "brain" that decides which agents to invoke after each step. Contains the intent-to-agent routing table, confidence-based routing (clarify if < 0.4, proceed if >= 0.7), missing-data checks (skip order agent if no order ID), and four conditional-edge functions (`route_after_intent`, `route_after_order`, `route_after_policy`, `route_after_risk`). |
| `src/orchestrator/evaluator.py` | **Quality gate** — runs after context-gathering agents and before response generation. Checks intent confidence, order context availability, policy retrieval completeness, product data presence, agent errors in the audit trail, and workflow action failures. Outputs a composite `quality_score` (0–1) and a list of `quality_issues`. |

### Agent Layer (`src/agents/`)

| File | Purpose |
|------|---------|
| `src/agents/intent_classifier.py` | **Intent Classification Agent** — classifies the customer message into one of 9 supported intents (order_tracking, return_request, refund_status, product_inquiry, warranty, coupon_issue, delivery_complaint, damaged_product, general_faq). Also detects sentiment (positive/neutral/negative/angry), urgency (low/medium/high/critical), and outputs a confidence score. Uses OpenAI function calling in live mode and keyword-based mock classification when `USE_MOCK=true`. |
| `src/agents/order_context.py` | **Order Context Agent** — retrieves unified order, shipment, payment, and CRM history for a customer. Tries to find order by direct order ID, then falls back to customer ID lookup. Returns structured order data (status, items, payment, shipment tracking, return history, CRM notes, customer tier) or an empty context with a clear "not found" signal. Currently uses a mock database. |
| `src/agents/policy_retrieval.py` | **Policy Retrieval Agent** — searches the policy knowledge base and returns matched policy snippets with reference IDs and confidence scores. Covers return, refund, warranty, coupon, delivery, and damaged-product policies. Currently uses keyword-to-policy lookup (to be replaced with RAG/vector retrieval). |
| `src/agents/product_advisory.py` | **Product Advisory Agent** — compares products, checks stock availability, and provides recommendations. Matches product keywords from the customer message against a mock product catalog (laptops, headphones) and returns side-by-side comparisons with specs, prices, ratings, and a recommendation summary. |
| `src/agents/workflow_automation.py` | **Workflow Automation Agent** — executes self-service actions based on intent: initiates returns, checks refund status, generates invoice links, creates support tickets, and updates shipping addresses. Flags sensitive high-value actions for human approval. Currently uses mock action functions. |
| `src/agents/escalation_risk.py` | **Escalation & Risk Agent** — evaluates risk using rule-based scoring (angry sentiment + high-value order, damaged high-value product, low classification confidence, lost shipment). Assigns a risk score (0–1), determines if escalation is required, and routes to the correct human team (fraud_review, refund_specialist, replacement_team, logistics, senior_agent) with a priority level (P1–P4). |
| `src/agents/response_generator.py` | **Response Generation Agent** — creates the final customer-facing response using all gathered context. Handles fallback scenarios (missing order data, no policy match, agent errors) with helpful fallback messages. In live mode, uses OpenAI to generate policy-grounded, channel-adapted, brand-aligned responses with cited references. In mock mode, uses template-based responses per intent. |

### Utility Layer (`src/utils/`)

| File | Purpose |
|------|---------|
| `src/utils/__init__.py` | **Package exports** — re-exports all utility functions for convenient importing (`from src.utils import get_logger, format_currency`, etc.). |
| `src/utils/logger.py` | **Structured logging** — provides `get_logger()` to create named loggers with both console and file output (`logs/system.log`), and `log_agent_step()` for standardized agent-level log entries with timestamps. |
| `src/utils/formatters.py` | **Display formatting** — `format_currency()` for INR/USD amounts, `format_timestamp()` for human-readable dates, `truncate_text()` for length-limited output, `format_agent_chain()` for pipeline visualization, `format_order_summary()` for one-line order summaries, and `mask_sensitive()` for masking card numbers and tokens. |
| `src/utils/validators.py` | **Input validation** — validates order IDs (`SE10234` format), customer IDs (`CUST_1001` format), intents, sentiments, urgency levels, channels, and confidence scores. Also provides `sanitize_user_input()` to strip dangerous characters and enforce length limits, and `extract_order_id_from_message()` to pull order IDs from free-text messages. |
| `src/utils/retry.py` | **Retry & error handling** — `retry_with_backoff()` decorator for exponential backoff on API calls, `graceful_fallback()` decorator to catch exceptions and return safe defaults, and `classify_error()` to categorize exceptions (api_error, timeout_error, auth_error, etc.) for metrics and routing. |
| `src/utils/metrics.py` | **Performance tracking** — `track_latency` decorator to measure agent execution time, `AgentMetrics` / `SessionMetrics` dataclasses for per-agent and per-session stats, `compute_resolution_metrics()` to aggregate batch results (resolution rate, escalation rate, avg confidence, intent distribution), and `get_agent_metrics()` / `reset_metrics()` for runtime inspection. |
| `src/utils/session.py` | **Session management** — `generate_session_id()` creates unique session IDs, `build_initial_state()` constructs a clean `AgentState` from raw customer input (sanitizes message, extracts order ID, sets defaults), and `append_to_history()` adds timestamped entries to conversation history. |

## Production Roadmap

The prototype uses JSON/CSV files for data. The architecture is designed so the data layer can be swapped to enterprise-grade services **without changing any agent or orchestration code**:

| Prototype | Production | Why |
|-----------|-----------|-----|
| JSON files | Azure Cosmos DB | Scalable NoSQL for orders, customers, products |
| Keyword matching | Azure AI Search | Vector embeddings for policy RAG retrieval |
| OpenAI API | Azure OpenAI Service | Enterprise SLA, data privacy, token budgets |
| Local logs | PostgreSQL | Audit compliance with SQL queries |
| In-memory | Redis | Session cache for multi-turn conversations |
| `python -m src.main` | Azure App Service | Auto-scaling hosted API |

All agent function signatures stay the same — just swap the implementation behind `get_order_status()`, `retrieve_policy()`, etc. See [`docs/architecture.md`](docs/architecture.md#8-scalability-and-production-deployment) for full details.

## Current Progress (as of Day 1)

### What's Built and Working

| Component | Status | Details |
|-----------|--------|---------|
| Git repo + GitHub remote | Done | All code on `main`, teammates have branch access |
| README + Architecture docs | Done | Full system design, agent contracts, state schema, mermaid diagrams |
| Team guides (Gunjan (Person 2)-5) | Done | Step-by-step instructions in `docs/team_guides/` |
| LangGraph orchestration graph | Done | `src/orchestrator/graph.py` — full pipeline with conditional routing |
| Shared state schema | Done | `src/orchestrator/state.py` — TypedDict flowing between all agents |
| Intent Classifier (OpenAI) | Done | `src/agents/intent_classifier.py` — GPT-4o + mock fallback |
| Router with confidence checks | Done | `src/orchestrator/router.py` — routes by intent, handles missing data |
| Evaluator / Quality Gate | Done | `src/orchestrator/evaluator.py` — checks completeness before response |
| Response Generator | Done | `src/agents/response_generator.py` — grounded responses with citations |
| Error-safe wrappers | Done | `src/orchestrator/graph.py` — no agent crash kills the pipeline |
| Fallback responses | Done | Asks for order ID, suggests specialist, requests clarification |
| Clarification path | Done | Low confidence (< 0.4) asks customer to rephrase |
| Helper utilities | Done | `src/utils/` — logger, validators, formatters, retry, metrics, session |
| Test suite | Done | `tests/` — resilience, intent, router tests (10+ 12 + 13 cases) |
| Scalability docs | Done | JSON-to-Azure migration path documented |
| 7 demo conversations | Done | `python -m src.main` runs all scenarios end-to-end |

### What's Pending (from Teammates)

| Who | What They Need to Deliver | Their Branch |
|-----|--------------------------|-------------|
| Gunjan (Person 2) | Policy KB (15+ rules), FAQ, Product catalog, RAG retrieval agent | Not started yet |
| Pallavi (Person 3) | Mock data JSONs, Order Context Agent, Workflow Agent, API functions | Not started yet |
| Aditi (Person 4) | Streamlit UI (customer chat + agent console), Product Advisory Agent | `ui-agent-aditi` (ready, not merged yet) |
| Rohan (Person 5) | Risk matrix, Escalation Agent, Audit logs, Evaluation suite, Final deck | Not started yet |

### How to Continue (for Next Cursor Session)

1. **Check for new branches:** `git fetch --all` then `git branch -r` to see teammate submissions
2. **Run the system:** `python -m src.main` (works in mock mode, no API key needed)
3. **Run with OpenAI:** Set `USE_MOCK=false` in `.env` and provide `OPENAI_API_KEY`
4. **When Gunjan (Person 2)/3 deliver:** Merge their branches, their code replaces the stubs in `src/agents/`
5. **When ready to integrate Aditi (Person 4):** Merge `ui-agent-aditi`, move files into `src/ui/`, wire to real orchestrator
6. **Final integration:** All agents use real data → run full evaluation → prepare presentation

### Key Design Decisions Made

- **LangGraph** for orchestration (not simple if/else) — gives us a real agent graph with conditional edges
- **OpenAI GPT-4o** for classification and response generation (with mock fallback for offline work)
- **Shared TypedDict state** — all agents read/write to one state object, no direct agent-to-agent calls
- **Error-safe wrappers** — any agent can fail without crashing the pipeline
- **Mock-first development** — system runs end-to-end without any external service
- **Confidence-based routing** — low confidence asks for clarification instead of guessing wrong
- **Aditi (Person 4)'s UI is separate for now** — will integrate after Gunjan (Person 2)/3 deliver real data

### Git History Summary

```
Day 1 commits (Ashish (Person 1)):
- Initial repo setup + README + architecture docs
- Full LangGraph orchestration with 7 agents
- Helper utilities (logger, validators, formatters, retry, metrics)
- Team guides for Gunjan (Person 2)-5
- Resilient routing + error handling + fallback responses
- Test suites
- Scalability documentation

Aditi (Person 4) (Aditi):
- Branch: ui-agent-aditi (Streamlit UI, product advisory, demo script)
- Status: Ready but not merged into main yet (waiting for P2/P3 data)
```

## License

This project is developed as a capstone for academic purposes.
