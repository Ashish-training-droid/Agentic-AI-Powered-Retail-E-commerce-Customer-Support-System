# ShopEase Agentic AI — Evaluation Report

- Cases file: `C:\Person5\Agentic-AI-Powered-Retail-E-commerce-Customer-Support-System\tests\evaluation\test_cases.json`
- USE_MOCK: `true`

## Headline metrics

| Metric | Value |
|--------|-------|
| Total cases | 25 |
| Pass rate | 68% (17/25) |
| Errors | 0 |
| Intent accuracy | 55% |
| Escalation precision | 100% |
| Escalation recall | 100% |
| False escalation rate | 0% |
| Avg quality score | 0.95 |
| Avg response confidence | 0.79 |
| Avg latency (ms) | 12.66 |

## Pass rate by category

| Category | Passed | Total | Rate |
|----------|-------:|------:|-----:|
| routine | 7 | 10 | 70% |
| escalation | 1 | 5 | 20% |
| edge_case | 4 | 5 | 80% |
| negative | 5 | 5 | 100% |

## Risk band distribution

| Band | Count |
|------|------:|
| auto | 18 |
| approval_required | 4 |
| escalate | 1 |

## Intent distribution (actual classifications)

| Intent | Count |
|--------|------:|
| order_tracking | 12 |
| general_faq | 10 |
| warranty | 1 |
| coupon_issue | 1 |
| damaged_product | 1 |

## Failing cases (8)

### TC_002 (routine)

**Message:** I want to return my Nike shoes from order SE10567

**Expected:** `{"intent": "return_request", "escalation": false, "min_confidence": 0.6, "should_have_policy_refs": true}`
**Actual intent:** `order_tracking`  /  **band:** `approval_required`  /  **team:** `escalation_queue`

- intent expected=return_request actual=order_tracking
- expected policy refs, none returned

### TC_003 (routine)

**Message:** When will my refund be credited? Order SE10567 returned 3 days ago.

**Expected:** `{"intent": "refund_status", "escalation": false, "should_have_policy_refs": true}`
**Actual intent:** `order_tracking`  /  **band:** `approval_required`  /  **team:** `escalation_queue`

- intent expected=refund_status actual=order_tracking
- expected policy refs, none returned

### TC_006 (routine)

**Message:** Compare HP Pavilion vs Lenovo IdeaPad for college student

**Expected:** `{"intent": "product_inquiry", "escalation": false, "risk_band": "auto"}`
**Actual intent:** `general_faq`  /  **band:** `auto`  /  **team:** `-`

- intent expected=product_inquiry actual=general_faq

### TC_012 (escalation)

**Message:** My package marked lost on order SE10111, the laptop never arrived

**Expected:** `{"intent": "delivery_complaint", "escalation_or_approval": true, "should_route_team_any": ["logistics", "senior_agent"]}`
**Actual intent:** `order_tracking`  /  **band:** `auto`  /  **team:** `-`

- intent expected=delivery_complaint actual=order_tracking
- expected escalation OR approval_required, got auto

### TC_013 (escalation)

**Message:** asdfgh zxcvbn random text

**Expected:** `{"escalation_or_approval_or_clarify": true}`
**Actual intent:** `general_faq`  /  **band:** `auto`  /  **team:** `-`

- expected escalation/approval/clarify, got auto

### TC_014 (escalation)

**Message:** I want a refund. Order SE10890. Please process immediately.

**Expected:** `{"intent": "refund_status", "should_route_team_any": ["refund_specialist", "senior_agent", "replacement_team"]}`
**Actual intent:** `order_tracking`  /  **band:** `auto`  /  **team:** `-`

- intent expected=refund_status actual=order_tracking

### TC_015 (escalation)

**Message:** I am very angry, this is the third time I am calling about my MacBook return. Order SE10567.

**Expected:** `{"escalation_or_approval": true, "sentiment_should_be_any": ["angry", "negative"]}`
**Actual intent:** `order_tracking`  /  **band:** `approval_required`  /  **team:** `escalation_queue`

- sentiment expected_one_of=['angry', 'negative'] actual=neutral

### TC_018 (edge_case)

**Message:** I want to return my order and also know warranty and refund and the coupon and where is my order this is a very long message with many intents in it please help me with all of these issues at once because i have many problems

**Expected:** `{"escalation_or_approval_or_clarify": true}`
**Actual intent:** `order_tracking`  /  **band:** `auto`  /  **team:** `-`

- expected escalation/approval/clarify, got auto
