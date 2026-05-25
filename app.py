"""
ShopEase Agentic AI — Customer Support System
==============================================
PwC Capstone Project | Run: streamlit run app.py
"""

from __future__ import annotations
import json as _json
import time
from datetime import datetime, timezone
from pathlib import Path as _Path

import streamlit as st

from src.orchestrator.graph import app as pipeline
from src.utils.session import build_initial_state, generate_session_id
from src.config import USE_MOCK

# ─────────────────────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="ShopEase AI Support", page_icon="🛒", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# PwC Theme Styling
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding-top: 0.5rem; max-width: 1400px; }
html, body, [class*="css"] { font-family: 'Georgia', 'Inter', sans-serif; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* PwC Header */
.pwc-header {
    background: linear-gradient(135deg, #000000 0%, #2D2D2D 100%);
    color: white; padding: 16px 24px; border-radius: 10px;
    margin-bottom: 16px; display: flex; align-items: center;
    justify-content: space-between;
}
.pwc-header-left { display: flex; align-items: center; gap: 12px; }
.pwc-logo {
    background: #D04A02; color: white; width: 36px; height: 36px;
    border-radius: 6px; display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.9rem;
}
.pwc-brand { font-size: 1.1rem; font-weight: 700; }
.pwc-sub { font-size: 0.72rem; color: #EB8C00; margin-top: 2px; }
.pwc-badge {
    background: rgba(208,74,2,0.2); color: #EB8C00;
    padding: 4px 10px; border-radius: 20px; font-size: 0.68rem;
    font-weight: 600; text-transform: uppercase;
}

/* PwC Accent Colors */
.stButton > button[kind="primary"] { background: #D04A02; border-color: #D04A02; color: white; }
.stButton > button[kind="primary"]:hover { background: #EB8C00; border-color: #EB8C00; }
[data-testid="stSidebar"] { background: #FAFAFA; border-right: 1px solid #E5E5E5; }
[data-baseweb="tab"][aria-selected="true"] { border-bottom-color: #D04A02 !important; color: #D04A02 !important; }

/* Chat styling */
.stChatMessage { border-radius: 8px; }
hr { margin: 0.5rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pwc-header">
  <div class="pwc-header-left">
    <div class="pwc-logo">SE</div>
    <div>
      <div class="pwc-brand">ShopEase AI Support</div>
      <div class="pwc-sub">Agentic AI | PwC Capstone</div>
    </div>
  </div>
  <div class="pwc-badge">Live Demo</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Load Customers
# ─────────────────────────────────────────────────────────────────────────────
def _load_customers():
    path = _Path(__file__).parent / "data" / "mock" / "customers.json"
    if not path.exists():
        return {"Rahul Patel (premium) - CUST_1001": "CUST_1001"}
    with open(path, "r", encoding="utf-8") as f:
        data = _json.load(f)
    custs = data.get("customers", data) if isinstance(data, dict) else data
    return {f"{c.get('name', '?')} ({c.get('tier', 'standard')}) - {c['customer_id']}": c["customer_id"] for c in custs}

CUSTOMERS = _load_customers()

DEMO_SCENARIOS = {
    "-- Choose --": {"message": "", "customer_id": "CUST_1001"},
    "Order Tracking": {"message": "Where is my order SE10234? It hasn't arrived yet.", "customer_id": "CUST_1001"},
    "Return Request": {"message": "I want to return the running shoes from order SE10567. They don't fit.", "customer_id": "CUST_1002"},
    "Damaged Product": {"message": "My Samsung Galaxy S24 arrived with a cracked screen! Order SE10890. Unacceptable!", "customer_id": "CUST_1003"},
    "Lost Shipment": {"message": "My order SE10999 is lost and never arrived. 2 weeks now!", "customer_id": "CUST_1001"},
    "Coupon Issue": {"message": "Coupon SAVE20 not working on my cart. Total is Rs 3500.", "customer_id": "CUST_1004"},
    "Product Compare": {"message": "Compare HP Pavilion and Lenovo IdeaPad for college.", "customer_id": "CUST_1004"},
    "Refund Status": {"message": "When will I get my refund? Returned shoes 5 days ago.", "customer_id": "CUST_1002"},
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
with st.sidebar:
    mode_text = "LIVE (GPT-4o)" if not USE_MOCK else "MOCK"
    st.markdown(f"**{mode_text}**")
    st.divider()

    scenario_choice = st.selectbox("Demo Scenario:", list(DEMO_SCENARIOS.keys()))
    scenario = DEMO_SCENARIOS[scenario_choice]

    selected_customer = st.selectbox("Customer:", list(CUSTOMERS.keys()),
        index=list(CUSTOMERS.values()).index(scenario["customer_id"]) if scenario["customer_id"] in CUSTOMERS.values() else 0)
    customer_id = CUSTOMERS[selected_customer]
    channel = st.selectbox("Channel:", ["web", "mobile", "email", "social"])

    st.divider()
    if st.button("Reset Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_result = None
        st.session_state.hitl_queue = []
        st.session_state.session_id = generate_session_id()
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────
def run(message: str):
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
    state = build_initial_state(message=message, customer_id=customer_id, channel=channel,
                                session_id=st.session_state.session_id, conversation_history=history)
    start = time.time()
    result = pipeline.invoke(state)
    result["_elapsed_ms"] = round((time.time() - start) * 1000)
    st.session_state.chat_history.append({"role": "user", "content": message})
    st.session_state.chat_history.append({"role": "assistant", "content": result.get("response_text", "")})
    st.session_state.last_result = result
    if result.get("risk_band") in ("approval_required", "escalate") or result.get("escalation_required"):
        st.session_state.hitl_queue.append({
            "time": datetime.now(timezone.utc).isoformat(), "customer_id": customer_id,
            "message": message, "intent": result.get("intent"), "risk_score": result.get("risk_score"),
            "risk_band": result.get("risk_band"), "target_team": result.get("target_team"),
            "priority": result.get("priority"), "draft_response": result.get("response_text"), "status": "pending",
        })
    return result

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_main, tab_hitl, tab_about = st.tabs(["Chat + Agent Console", "HITL Queue", "About"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: CHAT + AGENT CONSOLE (side by side)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_main:
    left, right = st.columns([0.40, 0.60], gap="large")

    # LEFT: Customer Chat
    with left:
        st.markdown("#### Customer Chat")
        chat_container = st.container(height=520, border=True)
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("**Hi! I'm ShopEase AI.** Ask me about orders, returns, refunds, products, or anything else.")
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_msg = st.chat_input("Type your message...")

        if scenario["message"] and not user_msg:
            if st.button(f'Send: "{scenario["message"][:50]}..."', use_container_width=True, type="primary"):
                user_msg = scenario["message"]

        if user_msg:
            run(user_msg)
            st.rerun()

    # RIGHT: Agent Console
    with right:
        st.markdown("#### Agent Console")
        result = st.session_state.last_result
        if not result:
            st.info("Send a message to see agent details.")
        else:
            # Summary metrics (3 columns to avoid truncation)
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"**Intent:** `{result.get('intent', '?')}`")
                st.markdown(f"**Sentiment:** {result.get('sentiment', '?')} | **Urgency:** {result.get('urgency', '?')}")
            with m2:
                st.markdown(f"**Confidence:** {result.get('intent_confidence', 0):.0%} | **Quality:** {result.get('quality_score', 0):.0%}")
                st.markdown(f"**Risk:** {result.get('risk_score', 0):.2f} | **Band:** `{result.get('risk_band', 'auto')}`")
            with m3:
                st.markdown(f"**Priority:** {result.get('priority', 'P4')} | **Latency:** {result.get('_elapsed_ms', 0)}ms")
                if result.get("escalation_required"):
                    st.markdown(f"**Team:** :red[{result.get('target_team')}]")
                else:
                    st.markdown(f"**Team:** N/A")

            agents = result.get("agents_called", [])
            if agents:
                st.code(" -> ".join(agents), language=None)

            # Toggle sections
            order_ctx = result.get("order_context", {})
            if order_ctx and order_ctx.get("order_id"):
                with st.expander("Order Context"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**Order:** `{order_ctx.get('order_id')}`")
                        st.write(f"**Status:** {order_ctx.get('status')}")
                        st.write(f"**Amount:** Rs {order_ctx.get('total_amount', 'N/A')}")
                    with c2:
                        ship = order_ctx.get("shipment", {})
                        if ship:
                            st.write(f"**Carrier:** {ship.get('carrier')}")
                            st.write(f"**Tracking:** `{ship.get('tracking')}`")
                            st.write(f"**ETA:** {ship.get('eta')}")
                    with c3:
                        cust = order_ctx.get("customer", {})
                        if cust:
                            st.write(f"**Name:** {cust.get('name')}")
                            st.write(f"**Tier:** {cust.get('tier')}")

            policies = result.get("policy_snippets", [])
            if policies:
                with st.expander("Policy (RAG Embeddings)"):
                    for p in policies:
                        st.write(f"`[{p.get('reference_id')}]` {p.get('rule', '')}")
                        st.caption(f"Similarity: {p.get('confidence', 0):.0%}")

            if result.get("action_taken"):
                with st.expander("Workflow Action"):
                    act = result.get("action_result", {})
                    st.write(f"**Action:** `{result.get('action_taken')}` | Success: {'Yes' if act.get('success') else 'No'}")
                    if act.get("message"): st.write(act['message'])

            with st.expander("Risk & Escalation"):
                r1, r2, r3 = st.columns(3)
                with r1: st.metric("Score", f"{result.get('risk_score', 0):.2f}")
                with r2: st.metric("Band", result.get("risk_band", "auto"))
                with r3: st.metric("Priority", result.get("priority", "P4"))
                if result.get("escalation_required"):
                    st.error(f"ESCALATED to **{result.get('target_team')}**")
                if result.get("risk_factors"):
                    for f in result["risk_factors"]:
                        st.caption(f"{f.get('name')}: {f.get('detail')}")

            with st.expander("Full Audit (JSON)"):
                st.json(result)

            if st.button("Export PDF", use_container_width=True, type="primary"):
                try:
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.cell(0, 10, "ShopEase AI - Audit Trail", ln=True, align="C")
                    pdf.set_font("Helvetica", "", 9)
                    pdf.cell(0, 6, f"Session: {st.session_state.session_id} | Customer: {customer_id} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ln=True)
                    pdf.ln(4)
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 6, f"Intent: {result.get('intent')} | Sentiment: {result.get('sentiment')} | Confidence: {result.get('intent_confidence', 0):.0%}", ln=True)
                    pdf.cell(0, 6, f"Risk: {result.get('risk_score', 0):.2f} | Band: {result.get('risk_band', 'auto')} | Priority: {result.get('priority', 'P4')}", ln=True)
                    if order_ctx and order_ctx.get("order_id"):
                        pdf.cell(0, 6, f"Order: {order_ctx.get('order_id')} | Status: {order_ctx.get('status')} | Rs {order_ctx.get('total_amount', 'N/A')}", ln=True)
                    pdf.ln(3)
                    pdf.set_font("Helvetica", "", 9)
                    if policies:
                        for p in policies:
                            pdf.cell(0, 5, f"[{p.get('reference_id')}] {p.get('rule', '')[:90]}", ln=True)
                    pdf.ln(3)
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 6, "Response:", ln=True)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.multi_cell(0, 5, result.get("response_text", "")[:600])
                    pdf.ln(2)
                    pdf.cell(0, 5, f"Agents: {' -> '.join(result.get('agents_called', []))}", ln=True)
                    st.download_button("Download PDF", data=pdf.output(), file_name=f"audit_{st.session_state.session_id[:8]}.pdf", mime="application/pdf", use_container_width=True)
                except ImportError:
                    st.error("Install fpdf2: pip install fpdf2")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: HITL QUEUE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_hitl:
    st.markdown("### Approval Queue")
    if not st.session_state.hitl_queue:
        st.info("No pending cases. Try 'Damaged Product' or 'Lost Shipment' scenario.")
    else:
        for i, case in enumerate(st.session_state.hitl_queue):
            with st.container(border=True):
                st.write(f"**{case['customer_id']}** | {case['intent']} | Risk: {case['risk_score']:.2f} | {case['priority']} | Team: {case['target_team']}")
                st.caption(f"Message: {case['message']}")
                if case.get("draft_response"):
                    st.code(case["draft_response"][:200], language=None)
                if case["status"] == "pending":
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("Approve", key=f"a{i}", type="primary"):
                            st.session_state.hitl_queue[i]["status"] = "approved"
                            st.session_state.chat_history.append({"role": "assistant", "content": f"[APPROVED] {case.get('draft_response', '')}"})
                            st.rerun()
                    with b2:
                        if st.button("Reject", key=f"r{i}"):
                            st.session_state.hitl_queue[i]["status"] = "rejected"
                            st.rerun()
                    with b3:
                        if st.button("Escalate", key=f"e{i}"):
                            st.session_state.hitl_queue[i]["status"] = "escalated"
                            st.rerun()
                else:
                    color = {"approved": "green", "rejected": "red", "escalated": "orange"}.get(case["status"], "grey")
                    st.markdown(f"**Status:** :{color}[{case['status'].upper()}]")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: ABOUT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown("""
### System Architecture
```
Customer Message → Intent Classifier (GPT-4o) → Router
    → Order Context | Policy RAG (Embeddings) | Product Advisory | Workflow
    → Evaluator → Risk Agent → Response Generator (GPT-4o) / Escalation
```

### Key Features
- **RAG with Embeddings** — semantic policy search, not keyword matching
- **Conversation Memory** — multi-turn context awareness
- **HITL Approval Queue** — risky cases get human review
- **7 AI Agents** collaborating through LangGraph
- **Error-safe Pipeline** — never crashes
- **PDF Audit Export** — compliance-ready trail

### Team
| Member | Role |
|--------|------|
| Ashish | Orchestrator, Intent, Response, RAG, CI |
| Gunjan | Policy KB, FAQ, RAG data |
| Pallavi | Mock APIs, Order Context, Workflows |
| Aditi | Product Advisory, UI Design |
| Rohan | Risk Agent, HITL, Evaluation |
    """)
