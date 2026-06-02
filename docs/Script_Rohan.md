# Rohan's Presentation Script

## Your Part: Demo — Escalation + Risk Scoring + HITL Queue

---

## DEMO: Damaged Product Escalation + HITL (after Aditi's product demo) — 1.5 minutes

### In the app (http://localhost:8501)

**Say:**

> "Now let me show you the safety layer — what happens when the AI shouldn't respond on its own.
>
> [Reset chat]
> [Select customer: Vikram Singh (VIP) - CUST_1003]
> [Select scenario: 'Damaged Product' -> Click Send]
>
> Watch the Agent Console on the right...
>
> [Point to the metrics]
>
> See: Intent is 'damaged_product', Sentiment is 'angry', Risk score is 0.57, Band is 'escalate'. The system decided this is TOO RISKY for AI to handle alone.
>
> Why? My Risk Agent uses a multi-factor weighted scoring engine — not simple if/else rules. Six factors:
>
> [Expand 'Risk & Escalation' toggle]
>
> 1. Sentiment: angry = 0.25 weight contribution
> 2. Order value: Rs 74,999 phone = high value = 0.20 contribution
> 3. Customer tier: VIP = faster escalation
> 4. Combined these factors pushed the score above the escalation threshold
>
> The system immediately:
> - Created a support ticket
> - Asked the customer for photos of the damage
> - Routed the case to the replacement team
>
> Now let me show you what the human reviewer sees.
>
> [Click 'HITL Queue' tab]
>
> This is our Human-in-the-Loop approval queue. The reviewer sees:
> - Customer ID, intent, risk score, priority (P2)
> - The target team (replacement_team)
> - The draft response that was generated
>
> They can:
> - Approve — sends the response to the customer
> - Reject — redirects to a specialist
> - Escalate Further — sends to a senior team
>
> [Click 'Approve']
>
> Done. The approved response goes to the customer. Every action is logged in the audit trail.
>
> This is the safety net. The AI generates the draft, but for high-risk cases, a human confirms before it reaches the customer. Zero risk of wrong promises on expensive items."

**[Hand over to Ashish for Analytics + Quick Actions]**

---

## Your Code Files (if asked)

```
src/agents/escalation_risk.py (536 lines) — Your risk engine:
  - WEIGHTS dict: sentiment 0.25, order_value 0.20, confidence 0.15, 
    customer_tier 0.10, repeated_contact 0.15, issue_severity 0.15
  - _factor_sentiment(), _factor_order_value(), etc. — each factor scored independently
  - _matched_routes(): evaluates all escalation rules, returns severity-sorted matches
  - _decide_band(): score + route severity -> auto / approval_required / escalate
  - ESCALATION_ROUTES: 7 routing rules (fraud, payment_dispute, damaged_high_value, 
    lost_shipment, angry_high_value, vip_attention, low_confidence)

src/governance/approval_queue.py — HITL system:
  - submit_for_approval(): parks draft response in queue
  - SLA tracking (2 hours for P1, 4 hours for P2, 8 hours for P3)
  - Status: pending -> approved / rejected / escalated

src/governance/audit.py — Audit trail:
  - build_audit_entry_from_state(): captures full pipeline output
  - save_audit_log(): durable JSONL log file
  - Every interaction traced for compliance

tests/test_escalation.py (443 lines) — Your tests:
  - Tests each risk factor independently
  - Tests routing decisions
  - Tests threshold boundaries
```

---

## Key Points to Emphasize

> "This isn't just 'if angry then escalate'. It's a WEIGHTED scoring system. A VIP customer with a Rs 75,000 damaged phone and angry sentiment — that's 3 factors combining. A regular customer asking politely about a Rs 500 item? Zero escalation needed."

> "The HITL queue means we never send an unreviewed response for high-risk cases. The AI does the work (generates the draft), the human does the judgment (approve or reject). Best of both worlds."
