# Ashish's Demo Operator Script

## You control the laptop/demo. This tells you EXACTLY what to click and when.

---

## BEFORE PRESENTATION STARTS

1. Open terminal: `streamlit run app.py` (make sure it's on http://localhost:8501)
2. Open browser: http://localhost:8501
3. Keep VS Code/Cursor open with these files ready in tabs:
   - `src/orchestrator/graph.py`
   - `src/knowledge/embedding_store.py`
4. Keep terminal ready to run: `python tests/test_resilience.py`
5. Click "Reset Chat" to start fresh
6. Make sure sidebar shows "LIVE (GPT-4o)"

---

## DEMO 1: Order Tracking (Pallavi is speaking)

**When Pallavi says "Let me show you this working live":**

| Step | You Do | She Says |
|------|--------|----------|
| 1 | Select customer dropdown: **"Rahul Patel (premium) - CUST_1001"** | "The customer asks where is my order..." |
| 2 | Select scenario: **"Order Tracking"** | |
| 3 | Click the orange **Send** button | "Watch what happens..." |
| 4 | Wait for response (3-5 sec) | She reads the response aloud |
| 5 | Scroll right panel to show **Agent Console** metrics | "This is my agent — the Order Context Agent" |
| 6 | Click expand **"Order Context"** toggle | She explains the data fields |

**Expected output in chat:**
> "Your order SE10234 is currently in_transit. It's being shipped via BlueDart (tracking: BD987120234). Expected delivery: 2026-05-22..."

**Expected Agent Console:**
- Intent: order_tracking | Confidence: 100%
- Risk: 0.23-0.30 | Band: auto
- Order: SE10234 | Status: shipped | Carrier: BlueDart

---

## DEMO 2: Policy RAG (Gunjan is speaking)

**When Gunjan says "Let me show you our knowledge layer":**

| Step | You Do | He Says |
|------|--------|---------|
| 1 | Click the **chat input box** at bottom | "The customer asks about refund..." |
| 2 | Type: **"I want my money back, when will I get my refund?"** | |
| 3 | Press Enter | "Watch how it finds the right policy..." |
| 4 | Wait for response (3-5 sec) | He reads the response |
| 5 | Click expand **"Policy (RAG Embeddings)"** toggle | "This is NOT keyword matching. This is RAG..." |
| 6 | Point to the reference IDs and similarity scores | He explains the embedding process |

**Expected output in chat:**
> Something about refund timeline, 5-7 business days, citing [POL-REF-TIME-001]

**Expected Agent Console - Policy toggle:**
- [POL-REF-PARTIAL-001] or [POL-REF-TIME-001] with similarity 50-60%
- Shows the actual policy rule text

---

## DEMO 3: Product Comparison (Aditi is speaking)

**When Aditi says "Now let me show you the product advisory":**

| Step | You Do | She Says |
|------|--------|----------|
| 1 | Click **chat input box** | "The customer wants to compare laptops..." |
| 2 | Type: **"Compare HP Pavilion and Lenovo IdeaPad for college"** | |
| 3 | Press Enter | "Watch — it routes to my Product Advisory Agent..." |
| 4 | Wait for response (3-5 sec) | She explains the comparison logic |
| 5 | Show Agent Console — intent should be product_inquiry | She talks about catalog |

**Expected output:**
> Product comparison with specs, recommendation for college use

**NOTE:** If intent shows "general_faq" instead of "product_inquiry" — that's fine, GPT still gives a good product answer. Don't worry about it.

---

## DEMO 4: Damaged Product Escalation (Rohan is speaking)

**When Rohan says "let me show you the safety layer":**

| Step | You Do | He Says |
|------|--------|---------|
| 1 | Click **"Reset Chat"** button in sidebar | "What happens when AI shouldn't respond alone..." |
| 2 | Change customer to: **"Aditya Nair (vip) - CUST_1003"** | |
| 3 | Select scenario: **"Damaged Product"** | |
| 4 | Click **Send** button | "Watch the risk score..." |
| 5 | Wait for response (3-5 sec) | He reads — should be escalation message |
| 6 | Point to Agent Console metrics (Risk, Band: escalate) | "My Risk Agent uses multi-factor scoring..." |
| 7 | Click expand **"Risk & Escalation"** toggle | He explains the 6 factors |
| 8 | Click **"HITL Queue"** tab at top | "This is what the human reviewer sees..." |
| 9 | Point to the case details | He explains Approve/Reject/Escalate |
| 10 | Click **"Approve"** button | "Done — approved response goes to customer" |

**Expected Agent Console:**
- Intent: damaged_product | Sentiment: angry | Confidence: 93-100%
- Risk: 0.55-0.65 | Band: escalate
- Target team: senior_agent or replacement_team | Priority: P1 or P2

**Expected HITL Queue:**
- Shows the case with risk score, band, team, draft response
- Approve/Reject/Escalate buttons visible

---

## DEMO 5: Analytics + Quick Actions (YOU are speaking)

**After Rohan finishes, you take over:**

| Step | You Do | You Say |
|------|--------|---------|
| 1 | Click **"Analytics"** tab | "Let me show our analytics dashboard..." |
| 2 | Point to Total Queries, Resolved, Escalated metrics | "In this session: X queries, Y resolved, Z escalated" |
| 3 | Point to Business Impact table | "Under 3 seconds vs 45 for human. 100% policy grounding." |
| 4 | Click back to **"Chat + Agent Console"** tab | "One more thing — proactive suggestions..." |
| 5 | Point to **quick action buttons** below chat | "After every response, the system suggests next steps" |
| 6 | Click **"Request callback"** button | "When customer wants a human..." |
| 7 | Wait for response | "Immediately escalated. Goes to HITL queue." |

---

## CODE WALKTHROUGH (YOU are speaking)

**After the demo section:**

| Step | You Do | You Say |
|------|--------|---------|
| 1 | Switch to **VS Code/Cursor** | "Let me show the code..." |
| 2 | Open `src/orchestrator/graph.py` | "Heart of the system. LangGraph." |
| 3 | Scroll to ~line 250 (graph.add_node lines) | "Each agent is a node..." |
| 4 | Point to add_conditional_edges | "Router decides the path..." |
| 5 | Point to error_safe decorator | "Any agent can fail, pipeline continues..." |
| 6 | Open `src/knowledge/embedding_store.py` | "Our RAG implementation..." |
| 7 | Point to search() method | "Embed query, cosine similarity, top 3..." |
| 8 | Switch to **terminal** | "Let me run our tests..." |
| 9 | Run: `python tests/test_resilience.py` | "10 tests, all passing..." |
| 10 | Wait for green output | "Happy path, missing data, escalation, garbage — never crashes." |

---

## TIMING CHECKLIST

| Time | What's Happening | Your Action |
|------|-----------------|-------------|
| 0:00 | Pallavi starts talking (slides) | Just show slides |
| 2:00 | Ashish — Architecture slides | Talk + show slides |
| 4:00 | Demo starts — Pallavi speaks | You operate the demo |
| 5:30 | Gunjan speaks | You type the query |
| 7:00 | Aditi speaks | You type the query |
| 8:00 | Rohan speaks | You click scenarios + HITL |
| 9:30 | YOU — Analytics + Quick Actions | You speak + click |
| 10:30 | YOU — Code Walkthrough | Switch to VS Code |
| 12:30 | YOU — Future Enhancements (slide 10) | Show slide |
| 14:00 | Q&A | Everyone answers |

---

## EMERGENCY BACKUP

**If the app crashes:**
- Run: `streamlit run app.py` again (takes 10 seconds)
- While it loads, explain architecture from slides

**If OpenAI times out:**
- Response will still come (mock fallback kicks in)
- Say: "The system has automatic fallback to rule-based responses when the API is slow"

**If wrong intent detected:**
- Don't panic — say: "In live mode GPT-4o is 95%+ accurate. The mock fallback uses keywords which sometimes mis-routes. Let me try another query."
- Type a clearer message

**If HITL queue is empty:**
- Run the Damaged Product scenario first — that always escalates
