# Person 5: Escalation, QA, Evaluation + Presentation Lead

## Your Role

You own **safety, quality, and proof** — the Escalation & Risk Agent, audit logs, the test suite, evaluation metrics, and the final presentation. You ensure the system is safe, measurable, and presentable.

## What You Need to Build

### 1. Escalation & Risk Agent (Week 2-3)

**Your main code file:** `src/agents/escalation_risk.py`

Replace the basic stub with a comprehensive risk engine.

**Risk scoring factors:**

| Factor | Weight | Signal |
|--------|--------|--------|
| Sentiment | 0.25 | angry = high risk, negative = moderate |
| Order value | 0.20 | > 10000 = high, > 5000 = moderate |
| Intent confidence | 0.15 | < 0.4 = escalate, < 0.7 = flag |
| Customer tier | 0.10 | VIP = lower threshold for escalation |
| Repeated contact | 0.15 | 3+ contacts on same issue = escalate |
| Issue severity | 0.15 | fraud, lost shipment, damaged = high |

**Build a proper risk matrix:**

```python
def calculate_risk_score(state: AgentState) -> float:
    """Multi-factor risk scoring."""
    score = 0.0
    
    # Sentiment factor
    sentiment_scores = {"positive": 0, "neutral": 0.1, "negative": 0.4, "angry": 0.8}
    score += sentiment_scores.get(state["sentiment"], 0.1) * 0.25
    
    # Order value factor
    order_value = state.get("order_context", {}).get("payment", {}).get("amount", 0)
    if order_value > 10000:
        score += 0.8 * 0.20
    elif order_value > 5000:
        score += 0.5 * 0.20
    
    # ... more factors ...
    
    return min(score, 1.0)
```

**Routing map — which team handles what:**

| Condition | Target Team | Priority | SLA |
|-----------|-------------|----------|-----|
| Fraud suspicion | fraud_review | P1 | 1 hour |
| Payment dispute/chargeback | refund_specialist | P2 | 4 hours |
| Damaged product > 10000 | replacement_team | P2 | 4 hours |
| Lost shipment | logistics + fraud | P2 | 4 hours |
| Angry VIP customer | senior_agent | P1 | 2 hours |
| Low confidence (< 0.4) | senior_agent | P3 | 8 hours |
| Repeated contact (3+ times) | escalation_queue | P3 | 8 hours |
| Policy exception needed | manager | P3 | 12 hours |

### 2. Audit Log System (Week 3-4)

Create `src/governance/audit.py` with proper audit trail:

```python
@dataclass
class AuditEntry:
    session_id: str
    timestamp: str
    customer_id: str
    intent_detected: str
    agents_called: list[str]
    policy_references: list[str]
    action_taken: str
    risk_score: float
    escalation: bool
    escalation_reason: str
    target_team: str
    response_confidence: float
    human_override: bool
    resolution_time_ms: float
    quality_score: float

def save_audit_log(entry: AuditEntry, filepath: str = "logs/audit.jsonl"):
    """Append audit entry to JSONL file for review."""
    ...

def load_audit_logs(filepath: str = "logs/audit.jsonl") -> list[AuditEntry]:
    """Load all audit entries for analysis."""
    ...

def generate_audit_report(logs: list[AuditEntry]) -> dict:
    """Generate summary statistics from audit logs."""
    ...
```

### 3. Evaluation Test Suite (Week 4-5)

Create `tests/evaluation/` with comprehensive test cases:

```
tests/
├── evaluation/
│   ├── test_cases.json         # 25+ test prompts with expected results
│   ├── run_evaluation.py       # Script to run all tests and score
│   └── evaluation_report.py    # Generate metrics report
├── test_intent_classifier.py   # Unit tests for intent accuracy
├── test_escalation.py          # Unit tests for risk rules
└── test_end_to_end.py          # Integration tests for full pipeline
```

**Test case structure (test_cases.json):**

```json
[
  {
    "id": "TC_001",
    "category": "routine",
    "message": "Where is my order SE10234?",
    "customer_id": "CUST_1001",
    "channel": "web",
    "expected": {
      "intent": "order_tracking",
      "sentiment": "neutral",
      "escalation": false,
      "should_contain": ["SE10234", "shipped", "BlueDart"],
      "should_not_contain": ["sorry", "escalat"],
      "min_confidence": 0.8
    }
  },
  {
    "id": "TC_015",
    "category": "edge_case",
    "message": "asdfghjkl gibberish random text",
    "customer_id": "CUST_1001",
    "channel": "web",
    "expected": {
      "intent": "general_faq",
      "escalation": true,
      "escalation_reason": "low_confidence"
    }
  }
]
```

**Minimum 25 test cases covering:**
- 10 routine cases (order, return, product, refund, coupon)
- 5 escalation cases (angry, high-value damaged, fraud signals, lost shipment)
- 5 edge cases (gibberish, multiple intents, very long message, empty message)
- 5 negative cases (should NOT give wrong policy, should NOT promise non-policy)

### 4. Evaluation Metrics (Week 5)

Build `tests/evaluation/run_evaluation.py`:

```python
def run_evaluation():
    """Run all test cases and compute metrics."""
    results = []
    for test in load_test_cases():
        state = build_initial_state(test["message"], test["customer_id"], test["channel"])
        output = app.invoke(state)
        score = evaluate_single(test, output)
        results.append(score)
    
    return {
        "intent_accuracy": ...,        # % correct intent classification
        "escalation_precision": ...,    # % correct escalation decisions
        "escalation_recall": ...,       # % of actual escalations caught
        "response_groundedness": ...,   # % of responses citing valid policy
        "avg_confidence": ...,
        "avg_quality_score": ...,
        "false_escalation_rate": ...,   # % incorrectly escalated
        "avg_resolution_time_ms": ...,
    }
```

**Target metrics for demo:**
- Intent accuracy: > 85%
- Escalation precision: > 80%
- Response groundedness: 100% (every factual claim has a reference)
- Average confidence: > 0.75

### 5. Final Presentation (Week 6)

**Your deck structure (15-20 slides):**

| Slide | Content | Speaker |
|-------|---------|---------|
| 1 | Title + team | Person 1 |
| 2-3 | Business problem + impact | Person 1 |
| 4-5 | Architecture + agent collaboration | Person 1 |
| 6-7 | Knowledge grounding + policy retrieval | Person 2 |
| 8-9 | Mock integrations + workflow demos | Person 3 |
| 10-12 | Customer chat + agent console UI | Person 4 |
| 13-14 | Escalation rules + safety | Person 5 |
| 15-16 | Evaluation metrics + test results | Person 5 |
| 17-18 | Business benefits + ROI | Person 5 |
| 19-20 | Limitations + future roadmap | Person 5 |

**Demo script (prepare for 5-minute live demo):**
1. Show order tracking (happy path) — 1 min
2. Show return request (policy + workflow) — 1 min
3. Show product comparison — 1 min
4. Show escalation (damaged high-value) — 1 min
5. Show agent console view — 1 min

## How to Test Your Work

```bash
# Test escalation scenarios
python -m src.main --demo 4   # Damaged product (should escalate)

# Run full evaluation
python tests/evaluation/run_evaluation.py

# Generate audit report
python -c "from src.governance.audit import generate_audit_report; ..."
```

## Handoff Partners

- **Person 1 (you report to):** Evaluation results validate the whole system
- **Person 2 (provides data):** Risk agent checks policy ambiguity from Person 2
- **Person 3 (provides data):** Risk agent checks order value and payment status

## Quality Checklist

- [ ] Risk agent uses at least 4 factors in scoring (not just if/else)
- [ ] All 7 escalation routes have a target team and priority
- [ ] Audit log captures every conversation with full trail
- [ ] 25+ test cases in evaluation suite
- [ ] Evaluation script runs and produces metrics report
- [ ] No false escalations in routine test cases
- [ ] All actual escalation cases are caught (100% recall on P1/P2)
- [ ] Final presentation has clear narrative flow
- [ ] Demo script tested end-to-end at least twice before presentation
- [ ] Metrics show measurable improvement over baseline (manual support)
