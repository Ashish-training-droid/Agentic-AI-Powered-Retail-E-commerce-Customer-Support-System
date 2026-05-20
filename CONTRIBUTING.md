# Contributing — ShopEase Agentic AI Support System

## Quick Start for Team Members

### 1. Clone and Setup

```bash
git clone https://github.com/Ashish-training-droid/Agentic-AI-Powered-Retail-E-commerce-Customer-Support-System.git
cd Agentic-AI-Powered-Retail-E-commerce-Customer-Support-System
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env and add your OpenAI API key (or set USE_MOCK=true)
```

### 3. Verify Everything Works

```bash
# Run in mock mode (no API key needed)
set USE_MOCK=true
python -m src.main
```

You should see all 7 demo conversations execute successfully.

### 4. Find Your Guide

Read your detailed task guide:
- Person 2: `docs/team_guides/PERSON_2_GUIDE.md`
- Person 3: `docs/team_guides/PERSON_3_GUIDE.md`
- Person 4: `docs/team_guides/PERSON_4_GUIDE.md`
- Person 5: `docs/team_guides/PERSON_5_GUIDE.md`

### 5. Your Code Files

Each person has specific files to work on. Look for `TODO(Person X)` markers:

| Person | Primary Files |
|--------|--------------|
| Person 2 | `src/agents/policy_retrieval.py`, `src/knowledge/policies/`, `src/knowledge/products/`, `src/knowledge/faqs/` |
| Person 3 | `src/agents/order_context.py`, `src/agents/workflow_automation.py`, `src/integrations/mock_apis/`, `data/mock/` |
| Person 4 | `src/agents/product_advisory.py`, `src/ui/customer_chat/`, `src/ui/agent_console/` |
| Person 5 | `src/agents/escalation_risk.py`, `src/governance/audit.py`, `tests/` |

## Git Workflow

### Branch Naming

```
feature/person2-policy-kb
feature/person3-mock-apis
feature/person4-chat-ui
feature/person5-evaluation
```

### Commit Convention

```
feat: add return policy rules (Person 2)
fix: order context handles missing data
docs: update evaluation metrics
```

### Pull Request Flow

1. Create a branch from `main`
2. Make your changes
3. Test with `python -m src.main`
4. Push and create a PR
5. Person 1 reviews and merges

## Important Rules

1. **Don't change function signatures** — The orchestrator calls your functions with a specific signature. Change the implementation, not the interface.

2. **Always return the expected state keys** — Check your agent's docstring for required output fields.

3. **Keep `agents_called` and `audit_trail`** — Every agent must append to these lists for traceability.

4. **Test with mock mode first** — Set `USE_MOCK=true` to run without API calls.

5. **Don't commit .env files** — They're in .gitignore for a reason.

## Project Structure

```
├── src/
│   ├── agents/           # All 7 AI agents
│   ├── orchestrator/     # LangGraph workflow, router, state, evaluator
│   ├── integrations/     # Mock APIs (Person 3)
│   ├── knowledge/        # Policy KB, products, FAQs (Person 2)
│   ├── ui/               # Customer chat + agent console (Person 4)
│   ├── governance/       # Audit logs (Person 5)
│   ├── utils/            # Shared helpers (logger, validators, formatters, etc.)
│   ├── config.py         # Configuration and thresholds
│   └── main.py           # Demo runner
├── data/mock/            # Mock data files (Person 3)
├── tests/                # Test suite (Person 5)
├── docs/                 # Architecture + team guides
├── logs/                 # Runtime logs (auto-created)
├── requirements.txt
└── .env.example
```

## How the Pipeline Works

```
Customer Message
      │
      ▼
┌─────────────────┐
│ Intent Classifier│ ──→ intent, sentiment, urgency, confidence
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Router Logic   │ ──→ decides which agents to call
└────────┬────────┘
         │
    ┌────┼────┬──────────┐
    ▼    ▼    ▼          ▼
 Order Policy Product  Workflow
Context Retrieval Advisory  Automation
    │    │    │          │
    └────┼────┴──────────┘
         │
         ▼
┌─────────────────┐
│   Evaluator     │ ──→ quality score, issues check
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Risk Check    │ ──→ escalate? or safe to respond?
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
Response   Escalation
Generator  to Human
    │         │
    └────┬────┘
         │
         ▼
  Final Customer Response
```

## Need Help?

- Architecture questions → Person 1
- Policy/data questions → Person 2
- API/workflow issues → Person 3
- UI/display issues → Person 4
- Testing/metrics → Person 5
