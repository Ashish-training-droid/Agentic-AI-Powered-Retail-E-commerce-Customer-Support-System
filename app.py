"""
ShopEase Agentic AI — Customer Support System (Full Demo)
=========================================================

Single unified app combining Aditi's professional UI design with
the real LangGraph multi-agent pipeline.

Run: streamlit run app.py
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import streamlit as st

from src.orchestrator.graph import app as pipeline
from src.utils.session import build_initial_state, generate_session_id
from src.config import USE_MOCK

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ShopEase Support — Agentic AI",
    page_icon="🛒",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Styling (from Aditi's design)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 1500px; }
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
h1 { font-size: 1.75rem !important; font-weight: 700 !important; color: #0F172A !important; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.se-header {
    background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
    color: white; padding: 18px 28px; border-radius: 12px;
    margin-bottom: 18px; display: flex; align-items: center;
    justify-content: space-between; box-shadow: 0 2px 8px rgba(15,23,42,0.06);
}
.se-header-left { display: flex; align-items: center; gap: 14px; }
.se-logo {
    background: #F25C05; color: white; width: 38px; height: 38px;
    border-radius: 8px; display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 1.1rem;
}
.se-brand-name { font-size: 1.15rem; font-weight: 700; }
.se-brand-tag { font-size: 0.78rem; color: #94A3B8; margin-top: 2px; }
.se-header-badge {
    background: rgba(242, 92, 5, 0.15); color: #FDBA74;
    padding: 5px 12px; border-radius: 999px; font-size: 0.72rem;
    font-weight: 600; text-transform: uppercase;
}
.se-section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #64748B; margin: 6px 0 8px 0;
}
[data-testid="stSidebar"] { background: #F7F8FA; border-right: 1px solid #E5E7EB; }
.stButton > button { border-radius: 8px; font-weight: 500; border: 1px solid #E5E7EB; }
.stButton > button[kind="primary"] { background: #F25C05; border-color: #F25C05; }
hr { margin: 0.75rem 0 !important; border-color: #E5E7EB !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="se-header">
  <div class="se-header-left">
    <div class="se-logo">SE</div>
    <div>
      <div class="se-brand-name">ShopEase Support</div>
      <div class="se-brand-tag">Agentic AI - Capstone Prototype</div>
    </div>
  </div>
  <div class="se-header-badge">LIVE DEMO</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Demo Scenarios
# ─────────────────────────────────────────────────────────────────────────────
DEMO_SCENARIOS = {
    "-- Choose a scenario --": {"message": "", "customer_id": "CUST_1001"},
    "S01 - Order tracking": {
        "message": "Where is my order SE10234? It hasn't arrived yet.",
        "customer_id": "CUST_1001",
    },
    "S02 - Return request": {
        "message": "I want to return the running shoes from order SE10567. They don't fit properly.",
        "customer_id": "CUST_1002",
    },
    "S03 - Damaged product (escalation)": {
        "message": "My Samsung Galaxy S24 arrived with a cracked screen! Order SE10890. This is completely unacceptable and I'm extremely frustrated!",
        "customer_id": "CUST_1003",
    },
    "S04 - Lost shipment (high value)": {
        "message": "My order SE10999 is lost and never arrived. It's been 2 weeks. This is unacceptable!",
        "customer_id": "CUST_1001",
    },
    "S05 - Coupon issue": {
        "message": "Why was my coupon SAVE20 not applied? My cart total is Rs 3500.",
        "customer_id": "CUST_1004",
    },
    "S06 - Product comparison": {
        "message": "Compare HP Pavilion and Lenovo IdeaPad laptop for college use. Which is better?",
        "customer_id": "CUST_1004",
    },
    "S07 - Refund status": {
        "message": "When will I get my refund? I returned my shoes 5 days ago.",
        "customer_id": "CUST_1002",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = generate_session_id()
    st.session_state.chat_history = []
    st.session_state.last_result = None
    st.session_state.hitl_queue = []

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
import json as _json
from pathlib import Path as _Path

def _load_customers():
    """Load all customers from mock data for the sidebar dropdown."""
    path = _Path(__file__).parent / "data" / "mock" / "customers.json"
    if not path.exists():
        return {"Rahul Patel (premium) - CUST_1001": "CUST_1001"}
    with open(path, "r", encoding="utf-8") as f:
        data = _json.load(f)
    custs = data.get("customers", data) if isinstance(data, dict) else data
    return {
        f"{c.get('name', 'Unknown')} ({c.get('tier', 'standard')}) - {c['customer_id']}": c["customer_id"]
        for c in custs
    }

CUSTOMERS = _load_customers()

with st.sidebar:
    mode = "LIVE (OpenAI GPT-4o)" if not USE_MOCK else "MOCK (offline)"
    st.markdown(f"**Mode:** {mode}")
    st.divider()

    st.markdown("### Quick Demo")
    st.caption("Pick a scenario and click Send — no typing needed during presentation.")
    scenario_choice = st.selectbox(
        "Scenario:",
        options=list(DEMO_SCENARIOS.keys()),
        index=0,
    )
    scenario = DEMO_SCENARIOS[scenario_choice]

    st.divider()

    st.markdown("### Customer")
    st.caption("Each customer has different orders, tier, and history.")
    selected_customer = st.selectbox(
        "Select customer:",
        options=list(CUSTOMERS.keys()),
        index=list(CUSTOMERS.values()).index(scenario.get("customer_id", "CUST_1001")) if scenario.get("customer_id") in CUSTOMERS.values() else 0,
    )
    customer_id = CUSTOMERS[selected_customer]
    channel = st.selectbox("Channel", ["web", "mobile", "email", "social"], label_visibility="collapsed")

    st.divider()
    if st.button("Reset conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_result = None
        st.session_state.hitl_queue = []
        st.session_state.session_id = generate_session_id()
        st.rerun()

    st.divider()
    st.caption("**Team:** Ashish | Gunjan | Pallavi | Aditi | Rohan")

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Runner
# ─────────────────────────────────────────────────────────────────────────────
def run(message: str):
    """Run the full LangGraph pipeline with conversation memory."""
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_history
    ]
    state = build_initial_state(
        message=message,
        customer_id=customer_id,
        channel=channel,
        session_id=st.session_state.session_id,
        conversation_history=history,
    )
    start = time.time()
    result = pipeline.invoke(state)
    result["_elapsed_ms"] = round((time.time() - start) * 1000)

    st.session_state.chat_history.append({"role": "user", "content": message})
    st.session_state.chat_history.append({"role": "assistant", "content": result.get("response_text", "")})
    st.session_state.last_result = result

    if result.get("risk_band") == "approval_required" or result.get("escalation_required"):
        st.session_state.hitl_queue.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "customer_id": customer_id,
            "message": message,
            "intent": result.get("intent"),
            "risk_score": result.get("risk_score"),
            "risk_band": result.get("risk_band"),
            "target_team": result.get("target_team"),
            "priority": result.get("priority"),
            "draft_response": result.get("response_text"),
            "status": "pending",
        })
    return result

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_chat, tab_hitl, tab_overview = st.tabs([
    "Customer Chat + Agent Console", "HITL Approval Queue", "System Overview"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Customer Chat + Agent Console (side by side)
# ─────────────────────────────────────────────────────────────────────────────
with tab_chat:
    left, right = st.columns([0.40, 0.60], gap="large")

    # LEFT: Customer Chat
    with left:
        st.markdown('<div class="se-section-label">CUSTOMER VIEW</div>', unsafe_allow_html=True)
        st.markdown("#### Customer Chat")

        chat_box = st.container(height=480, border=True)
        with chat_box:
            if not st.session_state.chat_history:
                st.info("Hi! I'm ShopEase Assist. Ask me about an order, return, refund, coupon, or product comparison. Or pick a demo scenario from the sidebar.")
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_msg = st.chat_input("Type your message...")

        if scenario["message"] and not user_msg:
            preview = scenario["message"][:60] + ("..." if len(scenario["message"]) > 60 else "")
            if st.button(f'Send: "{preview}"', use_container_width=True, type="primary"):
                user_msg = scenario["message"]

        if user_msg:
            run(user_msg)
            st.rerun()

    # RIGHT: Agent Console
    with right:
        st.markdown('<div class="se-section-label">INTERNAL VIEW</div>', unsafe_allow_html=True)
        st.markdown("#### Agent Console")

        result = st.session_state.last_result
        if not result:
            st.warning("Send a customer message to populate the console.")
        else:
            console = st.container(border=True)
            with console:
                # Intent & Classification
                st.markdown("**Intent Classification**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Intent", result.get("intent", "?"))
                with col2:
                    st.metric("Sentiment", result.get("sentiment", "?"))
                with col3:
                    st.metric("Confidence", f"{result.get('intent_confidence', 0):.0%}")
                with col4:
                    st.metric("Urgency", result.get("urgency", "?"))

                st.divider()

                # Order Context
                order_ctx = result.get("order_context", {})
                if order_ctx and order_ctx.get("order_id"):
                    st.markdown("**Order Context**")
                    oc1, oc2, oc3 = st.columns(3)
                    with oc1:
                        st.write(f"Order: `{order_ctx.get('order_id')}`")
                        st.write(f"Status: **{order_ctx.get('status')}**")
                        st.write(f"Amount: Rs {order_ctx.get('total_amount', 'N/A')}")
                    with oc2:
                        ship = order_ctx.get("shipment", {})
                        if ship:
                            st.write(f"Carrier: {ship.get('carrier', 'N/A')}")
                            st.write(f"Tracking: `{ship.get('tracking', 'N/A')}`")
                            st.write(f"ETA: {ship.get('eta', 'N/A')}")
                    with oc3:
                        cust = order_ctx.get("customer", {})
                        if cust:
                            st.write(f"Name: {cust.get('name', 'N/A')}")
                            st.write(f"Tier: **{cust.get('tier', 'regular')}**")
                            st.write(f"City: {cust.get('city', 'N/A')}")
                    st.divider()

                # Policy Retrieved
                policies = result.get("policy_snippets", [])
                if policies:
                    st.markdown("**Policy Retrieved**")
                    for p in policies:
                        st.write(f"`[{p.get('reference_id')}]` {p.get('rule', '')}")
                        st.caption(f"Confidence: {p.get('confidence', 0):.0%}")
                    st.divider()

                # Workflow Action
                if result.get("action_taken"):
                    st.markdown("**Workflow Action**")
                    act = result.get("action_result", {})
                    st.write(f"Action: `{result.get('action_taken')}`")
                    st.write(f"Success: {'Yes' if act.get('success') else 'No'}")
                    if act.get("message"):
                        st.write(f"Details: {act['message']}")
                    st.divider()

                # Risk Assessment
                st.markdown("**Risk & Escalation**")
                r1, r2, r3 = st.columns(3)
                with r1:
                    st.metric("Risk Score", f"{result.get('risk_score', 0):.2f}")
                with r2:
                    band = result.get("risk_band", "auto")
                    st.metric("Band", band)
                with r3:
                    st.metric("Priority", result.get("priority", "P4"))

                if result.get("escalation_required"):
                    st.error(f"ESCALATED to **{result.get('target_team')}** — {result.get('escalation_reason', '')}")
                elif band == "approval_required":
                    st.warning(f"Queued for human approval — Team: {result.get('target_team', 'N/A')}")

                st.divider()

                # Quality & Response
                st.markdown("**Response Quality**")
                q1, q2, q3 = st.columns(3)
                with q1:
                    st.metric("Quality Score", f"{result.get('quality_score', 0):.0%}")
                with q2:
                    st.metric("Response Confidence", f"{result.get('response_confidence', 0):.0%}")
                with q3:
                    st.metric("Latency", f"{result.get('_elapsed_ms', 0)}ms")

                if result.get("references_cited"):
                    st.write(f"References: {', '.join(result['references_cited'])}")

                st.divider()

                # Agent Pipeline Trace
                st.markdown("**Agent Pipeline**")
                agents = result.get("agents_called", [])
                if agents:
                    st.code(" -> ".join(agents), language=None)

                with st.expander("Raw audit log (JSON)"):
                    st.json(result)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: HITL Approval Queue
# ─────────────────────────────────────────────────────────────────────────────
with tab_hitl:
    st.markdown("### Human-in-the-Loop Approval Queue")
    st.caption("Cases requiring human review before response is served to the customer.")

    if not st.session_state.hitl_queue:
        st.info("No cases pending. Try 'Damaged product' or 'Lost shipment' scenario to trigger escalation.")
    else:
        for i, case in enumerate(st.session_state.hitl_queue):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**Customer:** {case['customer_id']} | **Intent:** {case['intent']} | **Priority:** {case['priority']}")
                    st.write(f"Message: _{case['message']}_")
                    if case.get("draft_response"):
                        st.code(case["draft_response"], language=None)
                with c2:
                    st.write(f"Risk: **{case['risk_score']:.2f}**")
                    st.write(f"Band: `{case['risk_band']}`")
                    st.write(f"Team: {case['target_team']}")
                    st.write(f"Status: **{case['status']}**")

                if case["status"] == "pending":
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("Approve & Send", key=f"approve_{i}", type="primary"):
                            st.session_state.hitl_queue[i]["status"] = "approved"
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": f"[APPROVED by agent] {case.get('draft_response', '')}",
                            })
                            st.rerun()
                    with b2:
                        if st.button("Reject", key=f"reject_{i}"):
                            st.session_state.hitl_queue[i]["status"] = "rejected"
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": "I apologize, but I need to transfer you to a specialist who can better assist with your case. They'll reach out shortly.",
                            })
                            st.rerun()
                    with b3:
                        if st.button("Escalate Further", key=f"esc_{i}"):
                            st.session_state.hitl_queue[i]["status"] = "escalated"
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": "Your case has been escalated to a senior specialist. They will contact you within 1 hour with a resolution.",
                            })
                            st.rerun()
                elif case["status"] == "approved":
                    st.success("Approved — response sent to customer.")
                elif case["status"] == "rejected":
                    st.error("Rejected — customer redirected to specialist.")
                elif case["status"] == "escalated":
                    st.warning("Escalated — senior specialist assigned.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: System Overview
# ─────────────────────────────────────────────────────────────────────────────
with tab_overview:
    st.markdown("### System Architecture")
    st.markdown("""
```
Customer Message
      |
      v
[Intent Classifier] -> intent, sentiment, urgency, confidence
      |
      v
[Router] -> decides which agents to call based on intent
      |
  +---+---+----------+
  v   v   v          v
Order Policy Product Workflow
  |   |   |          |
  +---+---+----------+
      |
      v
[Evaluator] -> quality check
      |
      v
[Risk Agent] -> auto / approval_required / escalate
      |
  +---+---+
  v       v
Auto    HITL/Escalate
Respond  to Human
```
    """)

    st.divider()
    st.markdown("### 7 AI Agents")
    st.table({
        "Agent": ["Intent Classifier", "Order Context", "Policy Retrieval", "Product Advisory", "Workflow Automation", "Escalation & Risk", "Response Generator"],
        "Owner": ["Ashish", "Pallavi", "Gunjan", "Aditi", "Pallavi", "Rohan", "Ashish + Aditi"],
        "What It Does": [
            "Classifies intent, sentiment, urgency from customer message",
            "Fetches order, payment, shipment, CRM data",
            "Searches policy KB, returns matched rules with citations",
            "Compares products, recommends alternatives",
            "Executes returns, refunds, tickets, invoices",
            "Multi-factor risk scoring, HITL routing",
            "Generates grounded, policy-cited customer response",
        ],
    })

    st.divider()
    st.markdown("### Key Features")
    st.markdown("""
    - **Conversation Memory** — system remembers context across messages
    - **Confidence-based Routing** — low confidence asks for clarification
    - **HITL Approval Queue** — risky cases get human review
    - **Error-safe Pipeline** — no agent crash kills the system
    - **Policy Grounding** — every claim cites a reference
    - **Multi-factor Risk Scoring** — sentiment + value + history + confidence
    """)
