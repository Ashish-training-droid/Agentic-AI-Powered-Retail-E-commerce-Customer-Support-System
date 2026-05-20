# Person 2: Knowledge Base + Policy Retrieval Engineer

## Your Role

You own the **trusted knowledge layer** — every answer our system gives must be grounded in your policy documents and product catalog. Without your work, the AI cannot give accurate or consistent answers.

## What You Need to Build

### 1. Policy Knowledge Base (Week 1-2)

Create policy documents covering all ShopEase rules. Store them in `src/knowledge/policies/`.

**Files to create:**

```
src/knowledge/policies/
├── return_policy.json
├── refund_policy.json
├── warranty_policy.json
├── delivery_policy.json
├── coupon_policy.json
├── seller_policy.json
└── general_faq.json
```

**Each policy entry should have this structure:**

```json
{
  "policy_id": "POL-RET-ELEC-001",
  "category": "return",
  "subcategory": "electronics",
  "rule": "Electronics can be returned within 7 days of delivery if unopened and in original packaging.",
  "conditions": [
    "Item must be within 7 days of delivery",
    "Item must be unopened",
    "Original packaging must be intact"
  ],
  "exceptions": [
    "Software licenses are non-returnable",
    "Customized items cannot be returned"
  ],
  "applicable_to": ["electronics", "accessories"],
  "effective_from": "2026-01-01",
  "last_updated": "2026-05-01"
}
```

**Policies to write (minimum 15-20 rules):**

| Area | Examples |
|------|----------|
| Returns | Electronics 7 days, Fashion 15 days, Groceries non-returnable, conditions for each |
| Refunds | Timeline by payment method (UPI 24hr, Card 5-7 days, EMI reversal), partial refund rules |
| Warranty | Manufacturer warranty periods, what's covered vs not, claim process |
| Delivery | Shipping fee refund if delayed 3+ days, redelivery attempts, address change cutoff |
| Coupons | Min cart value, category restrictions, stacking rules, expiry, first-order coupons |
| Seller | Seller-fulfilled vs ShopEase-fulfilled differences, dispute resolution |

### 2. FAQ Repository (Week 1-2)

Create `src/knowledge/faqs/faq_database.json` with 20+ common Q&A pairs:

```json
{
  "faq_id": "FAQ-PAY-001",
  "question": "What payment methods do you accept?",
  "answer": "We accept UPI, credit/debit cards, net banking, wallets (Paytm, PhonePe), and EMI on select cards.",
  "category": "payments",
  "keywords": ["payment", "pay", "UPI", "card", "EMI", "wallet"]
}
```

### 3. Product Catalog (Week 1-2)

Create `src/knowledge/products/catalog.json` with 15-20 products:

```json
{
  "product_id": "WH-100",
  "name": "Sony WH-1000XM5",
  "category": "electronics",
  "subcategory": "headphones",
  "price": 24999,
  "specs": {
    "type": "Over-ear",
    "anc": true,
    "battery_hours": 30,
    "connectivity": "Bluetooth 5.2",
    "weight_grams": 250
  },
  "rating": 4.7,
  "reviews_count": 1240,
  "in_stock": true,
  "coupon_eligible": true,
  "return_window_days": 7,
  "warranty_months": 12,
  "best_for": ["travel", "work from home", "music lovers"],
  "alternatives": ["JBL Tune 770NC", "Bose QC45"]
}
```

### 4. Policy Retrieval Agent (Week 2-3)

**Your main code file:** `src/agents/policy_retrieval.py`

Replace the mock implementation with actual retrieval. Two approaches (pick one):

**Option A: Vector/RAG Retrieval (recommended for demo impact)**

```python
# Install: pip install chromadb sentence-transformers
from chromadb import Client
from sentence_transformers import SentenceTransformer

# 1. Load all policies into ChromaDB at startup
# 2. Embed the customer query
# 3. Search for top-k matching policies
# 4. Return with confidence scores
```

**Option B: Keyword + Rule Matching (simpler, still effective)**

```python
# 1. Parse intent and extract keywords from message
# 2. Match against policy conditions and categories
# 3. Rank by relevance
# 4. Return top matches with reference IDs
```

**Your function signature (don't change it):**

```python
def retrieve_policy(state: AgentState) -> AgentState:
    # Reads: intent, message, order_context
    # Writes: policy_snippets, policy_applies, agents_called, audit_trail
```

**Output format (must return this structure):**

```python
{
    "policy_snippets": [
        {
            "rule": "...",
            "explanation": "...",
            "reference_id": "POL-XXX-YYY-001",
            "confidence": 0.92
        }
    ],
    "policy_applies": True,
    "agents_called": ["policy_retrieval"],
    "audit_trail": [{"agent": "policy_retrieval", ...}]
}
```

### 5. Grounding Validation (Week 4-5)

Create `tests/test_grounding.py` — verify that responses never contradict policy:

- 10 test cases where the correct policy should be returned
- 5 edge cases (ambiguous situations)
- Verify reference_id is always present when policy applies

## How to Test Your Work

```bash
# Run the full pipeline with your policies
python -m src.main --demo 2   # Return request
python -m src.main --demo 5   # Coupon issue
python -m src.main --demo 6   # Refund status
```

## Dependencies You May Add

Add these to `requirements.txt` if using RAG:
```
chromadb>=0.5.0
sentence-transformers>=3.0.0
```

## Handoff Partners

- **Person 1 (you report to):** Your policy snippets feed into the Response Generator
- **Person 5 (uses your output):** Risk agent checks if policy is ambiguous for escalation

## Quality Checklist

- [ ] At least 15 policy rules across all 6 categories
- [ ] Each policy has a unique reference_id (format: POL-XXX-YYY-NNN)
- [ ] FAQ covers at least 20 common questions
- [ ] Product catalog has 15+ products with full specs
- [ ] Retrieval returns correct policy for 10 test questions
- [ ] No response is given without a matching policy when policy applies
- [ ] Confidence scores are meaningful (high for exact match, lower for partial)
