# Demo Script — Person 4 UI Module

A 4-5 minute walkthrough of the ShopEase Agentic AI customer support
prototype. Use this as your speaker notes during the final capstone
presentation.

---

## Before you start

1. Open a terminal in `shopease_capstone/`.
2. Run `streamlit run app.py`. Wait until you see the browser open.
3. Maximize the browser window. The side-by-side layout needs the full width.
4. Click **🔄 Reset conversation** in the sidebar to start clean.

---

## Opening (30 seconds)

> "I'm Person 4 on this team. I built the customer chat, the support
> agent console, and the Product Advisory Agent. The other six agents
> you'll see on the right are owned by my teammates — but to make this
> UI demoable today, I built mock versions of each that follow the same
> input/output contracts. When their real agents land, we swap them in
> without touching the UI."

Point to:
- The sidebar → "These are the seven canned scenarios I'll walk through."
- The two side-by-side panels → "Customer view on the left, agent view on the right."
- The Product Comparison tab → "We'll come back to that — it's the agent I actually own."

---

## Scenario S01 — Order tracking (45 seconds)

**Sidebar action:** pick "S01 · Order tracking", click "Send scenario message".

> "A customer asks 'Where is my order SE10234?'. Watch what the system
> does in one step."

Point at the right panel as you talk:

- **Intent panel** → "Intent classifier detected 'Order Tracking' with 0.85 confidence and Neutral sentiment."
- **Order Context panel** → "Order Context Agent pulled the order from our mock API: Galaxy A55, in transit with BlueDart, ETA the 22nd, weather delay flagged."
- **Workflow Result** → "Workflow agent ran `track_shipment` and completed it."
- **Evaluator Score** → "Person 5's evaluator gave this turn 65/100 — good, not great because there's no policy invoked for a routine tracking question."

> "The customer sees a clean reply on the left with the ETA and the
> delay reason. The agent on the right sees the whole audit trail."

---

## Scenario S03 — Damaged product (60 seconds, the emotional one)

**Sidebar action:** Reset, pick "S03 · Damaged product".

> "Now something harder. The customer says: 'My Sony headphones arrived
> cracked! This is unacceptable.' Three things have to happen at once —
> understand the emotion, find the policy, raise a ticket."

Point out:

- **Intent panel** → "Damaged Product, sentiment Frustrated, urgency High. The system reads the tone, not just the words."
- **Policy panel** → "Person 2's Policy Retrieval Agent fetched RETURN-002, the 'Damaged on Arrival' rule. Notice the response on the left actually cites that policy — we're not making things up."
- **Workflow** → "Workflow agent created ticket ESC-10236 and marked it Escalated."
- **Risk panel** → "Risk score 2, level Medium, routed to the Replacement Team. The reasons list shows exactly why."
- **Evaluator** → "90/100 this time — intent confident, policy grounded, workflow ran, risk handled."

> "This is what we mean by 'agentic'. Six different specialist agents
> contributed to one customer reply, and you can see each contribution
> in the trace at the bottom."

---

## Scenario S04 — Lost shipment (60 seconds, the headline moment)

**Sidebar action:** Reset, pick "S04 · Lost shipment (high value)".

> "This is the case ShopEase fears most: a high-value item, lost in
> transit, with an angry customer. Watch how the risk agent handles it."

Point out:

- **Headline metrics** → "Risk: **High**. That's the only High-risk badge in the demo."
- **Order panel** → "Total ₹99,999. Shipment status: Lost in Transit. We can see the customer already filed an escalation 5 days ago."
- **Risk panel** → "Risk score 8. Reasons: high-impact intent, high-value order, shipment marked lost, frustrated sentiment. Routed to **Logistics + Senior Agent** — not a junior agent. That's the kind of routing decision that protects customer relationships."
- **Customer reply on the left** → "Notice the tone — empathetic, cites the policy, gives the customer a ticket number and tells them who's handling it."

---

## Scenario S05 — Coupon issue (40 seconds)

**Sidebar action:** Reset, pick "S05 · Coupon issue".

> "A common but frustrating one: 'Why was my FESTIVE10 coupon not
> applied?'. Customers get a different answer from every agent today —
> our system grounds the answer in the actual coupon policy."

Point out:

- **Policy panel** → "Notice it's not the generic coupon policy. The retriever spotted 'FESTIVE10' in the message and pulled the coupon-specific rule: minimum order ₹30,000."
- **Customer reply** → "The customer's order was ₹22,499. The reply explains exactly why the coupon didn't apply, using the policy's own words."
- **Evaluator** → "100/100 — perfect grounding, completed workflow, no risk."

---

## Scenario S06 — Product comparison (60 seconds, my agent)

**Sidebar action:** Reset, pick "S06 · Product comparison".

> "This is the agent I actually own end-to-end. The customer says
> 'Compare IdeaBook Slim 5 vs Aspire 14 Pro for college use.'"

Point at the right panel:

- **Product Advisory card** → "Recognized both products, picked IdeaBook Slim 5, and explained why: higher rating, longer battery, more RAM."

Then switch to **Tab 2 — Product Comparison** for a richer view:

1. Category: Laptop, Product A: IdeaBook Slim 5, Product B: Aspire 14 Pro, Use case: College.
2. Click **🔍 Compare**.
3. > "Side-by-side spec table — processor, RAM, storage, battery, weight,
>    warranty. The recommendation explains itself in plain English."
4. Open **How the recommendation was scored** expander.
   > "Transparent scoring: each product gets a single number, and the
>    higher number wins. No black box."
5. Scroll to the **out-of-stock helper**. Pick `ZenBook 14 OLED`.
   > "If a customer asks about an out-of-stock item, the agent doesn't
>    just say no — it offers in-stock alternatives in the same category,
>    ranked by rating."

---

## Closing (30 seconds)

> "Across seven scenarios, the system did three things consistently:
> it understood the customer, it grounded the response in policy, and
> it escalated only the cases that genuinely needed a human. The agent
> console gives support staff a single view of all that reasoning, which
> is what reduces the productivity gap mentioned in the problem
> statement. Mock backends today, real backends from my teammates next —
> the UI is ready for both. Happy to take questions."

---

## Backup plan if live demo fails

1. The presentation deck has screenshots of every scenario.
2. The pipeline is deterministic — re-running the same scenario gives the
   same output. If a panel doesn't render, hit Reset and pick the
   scenario again.
3. If Streamlit itself dies, fall back to the `DEMO_SCRIPT.md` you're
   reading right now and walk through the screenshots in the deck.

---

## What to capture for screenshots

For the final PPT, the strongest single screenshot is **S04 with the
console fully populated**: it shows High risk, the escalation routing,
the policy citation, and the customer-facing reply all at once.

Other screenshots worth having:
- S03 console (shows damaged-product flow)
- S06 + Tab 2 comparison table (shows your signature agent)
- Tab 2 out-of-stock helper (shows the alternative-recommendation flow)
