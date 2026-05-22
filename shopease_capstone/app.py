"""
ShopEase Agentic AI — Customer Support Prototype
=================================================

Person 4 module: customer chat UI + agent-assist console + product advisory.

HOW TO RUN:
    pip install streamlit pandas
    streamlit run app.py

WHAT'S ON SCREEN:
    Tab 1 "Customer Chat + Agent Console"
        Left  -> what the shopper sees (chat bubbles)
        Right -> what the support agent sees (every agent's output)
    Tab 2 "Product Comparison"
        Side-by-side spec table, scored recommendation, out-of-stock helper.
    Tab 3 "About"
        Integration notes — which function each teammate replaces later.

PROJECT STRUCTURE:
    shopease_capstone/
    ├── app.py                       <- this file (Streamlit entry point)
    ├── data/
    │   ├── products.csv             <- 15 products incl. laptops, phones, headphones
    │   ├── orders.json              <- 5 mock orders covering all demo scenarios
    │   └── policies.json            <- return/refund/warranty/delivery/coupon rules
    └── modules/
        ├── mock_agents.py           <- simulated back-end agents (mocked for now)
        ├── product_advisory.py      <- Person 4's signature agent (the real one)
        └── ui_components.py         <- reusable Streamlit panels
"""

from __future__ import annotations

import streamlit as st

# Import the renamed agent functions and helpers.
from modules import product_advisory as pa
from modules.mock_agents import run_full_pipeline, run_real_pipeline, _REAL_BACKEND_AVAILABLE
from modules.ui_components import (
    render_agent_trace,
    render_evaluation_panel,
    render_intent_panel,
    render_order_panel,
    render_policy_panel,
    render_product_comparison,
    render_risk_panel,
    render_workflow_panel,
)

# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
# Wide layout is essential — we have a chat on the left and a busy dashboard
# on the right; they wouldn't fit in the default narrow layout.

st.set_page_config(
    page_title="ShopEase Support — Agentic AI",
    page_icon="🛒",
    layout="wide",
)

# Brand-grade visual styling: corporate dashboard look, ShopEase orange accent,
# tightened typography, hidden Streamlit chrome, and reusable card/section classes.
st.markdown(
    """
    <style>
    /* ---------- Layout ---------- */
    .block-container {
      padding-top: 1rem;
      padding-bottom: 1rem;
      max-width: 1500px;
    }

    /* ---------- Typography ---------- */
    html, body, [class*="css"] {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    h1 {
      font-size: 1.75rem !important;
      font-weight: 700 !important;
      color: #0F172A !important;
      letter-spacing: -0.02em;
    }
    h2, h3 { color: #0F172A !important; }

    /* ---------- Hide Streamlit chrome ---------- */
    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    /* ---------- Brand header bar ---------- */
    .se-header {
      background: linear-gradient(90deg, #0F172A 0%, #1E293B 100%);
      color: white;
      padding: 18px 28px;
      border-radius: 12px;
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 8px rgba(15,23,42,0.06);
    }
    .se-header-left { display: flex; align-items: center; gap: 14px; }
    .se-logo {
      background: #F25C05;
      color: white;
      width: 38px; height: 38px;
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 1.1rem;
      font-family: 'Inter', sans-serif;
    }
    .se-brand-name { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.01em; }
    .se-brand-tag  { font-size: 0.78rem; color: #94A3B8; margin-top: 2px; }
    .se-header-badge {
      background: rgba(242, 92, 5, 0.15);
      color: #FDBA74;
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] { background: #F7F8FA; border-right: 1px solid #E5E7EB; }
    [data-testid="stSidebar"] .stMarkdown h3 {
      font-size: 0.72rem !important;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748B !important;
      margin-top: 1rem;
      font-weight: 700 !important;
    }

    /* ---------- Cards / containers ---------- */
    [data-testid="stVerticalBlockBorderWrapper"] {
      border-radius: 12px !important;
      border-color: #E5E7EB !important;
      box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    }

    /* ---------- Tabs ---------- */
    [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #E5E7EB; }
    [data-baseweb="tab"] {
      background: transparent;
      padding: 10px 16px;
      font-weight: 500;
      color: #64748B;
    }
    [data-baseweb="tab"][aria-selected="true"] {
      color: #0F172A;
      border-bottom: 2px solid #F25C05 !important;
    }

    /* ---------- Buttons ---------- */
    .stButton > button {
      border-radius: 8px;
      font-weight: 500;
      border: 1px solid #E5E7EB;
    }
    .stButton > button[kind="primary"] {
      background: #F25C05;
      border-color: #F25C05;
    }
    .stButton > button[kind="primary"]:hover { background: #D94F00; border-color: #D94F00; }

    /* ---------- Chat bubbles ---------- */
    .stChatMessage { border-radius: 10px; border: 1px solid #E5E7EB; }

    /* ---------- Section labels ---------- */
    .se-section-label {
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #64748B;
      margin: 6px 0 8px 0;
    }

    /* ---------- Divider tightening ---------- */
    hr { margin: 0.75rem 0 !important; border-color: #E5E7EB !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Demo scenarios
# -----------------------------------------------------------------------------
# Each scenario pre-fills the chat with a realistic customer query and the
# matching order ID. The presenter just picks one from the sidebar and clicks
# "Send" — no live typing during the demo means no typos in front of evaluators.

DEMO_SCENARIOS = {
    "— Choose a scenario —": {"message": "", "order_id": ""},
    "S01 · Order tracking": {
        "message": "Where is my order SE10234? It hasn't arrived yet.",
        "order_id": "SE10234",
    },
    "S02 · Return request": {
        "message": "I want to return my laptop from order SE10235.",
        "order_id": "SE10235",
    },
    "S03 · Damaged product (high urgency)": {
        "message": "My Sony headphones arrived cracked! Order SE10236. This is unacceptable.",
        "order_id": "SE10236",
    },
    "S04 · Lost shipment (high value)": {
        "message": "My MacBook order SE10237 is lost. It's been 14 days, I am very frustrated!",
        "order_id": "SE10237",
    },
    "S05 · Coupon issue": {
        "message": "Why was my FESTIVE10 coupon not applied on order SE10238?",
        "order_id": "SE10238",
    },
    "S06 · Product comparison": {
        "message": "Compare IdeaBook Slim 5 vs Aspire 14 Pro for college use.",
        "order_id": "",
    },
    "S07 · Invoice request": {
        "message": "Can I get the invoice for order SE10235?",
        "order_id": "SE10235",
    },
}


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
# Streamlit reruns the whole script on every interaction, so we keep the
# chat history and the latest pipeline output in `st.session_state` to
# survive those reruns.

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of {"role": "user"|"assistant", "content": str}
if "last_state" not in st.session_state:
    st.session_state.last_state = None   # the most recent pipeline output


# -----------------------------------------------------------------------------
# Sidebar — scenario selector + order/customer inputs + team credits
# -----------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px;'>
          <div class="se-logo" style="width:28px;height:28px;font-size:0.85rem;">SE</div>
          <div style='font-weight:700;font-size:1rem;color:#0F172A;'>ShopEase</div>
        </div>
        <div style='font-size:0.78rem;color:#64748B;margin-bottom:10px;'>
          Agentic AI Customer Support
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### 🎬 Demo Scenarios")
    scenario_choice = st.selectbox(
        "Pick a scenario to auto-fill the chat:",
        options=list(DEMO_SCENARIOS.keys()),
        index=0,
        key="scenario_picker",
    )
    scenario = DEMO_SCENARIOS[scenario_choice]

    st.markdown("### 🆔 Optional Inputs")
    order_id_input = st.text_input(
        "Order ID (optional)",
        value=scenario["order_id"],
        help="Used by Order Context Agent to fetch order details.",
    )
    customer_id_input = st.text_input(
        "Customer ID (optional)",
        value="",
        # TODO: Person 3 — wire this to the CRM mock once available.
        help="Wire-ready for when Person 3's CRM mock is connected.",
    )

    st.divider()
    # A reset button is essential during the demo — if a scenario goes
    # sideways, the presenter needs a clean slate in one click.
    if st.button("🔄 Reset conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_state = None
        st.rerun()

    st.divider()
    st.markdown("### ⚙️ Backend")
    backend_mode = st.radio(
        "Pipeline:",
        options=["Real (Team LangGraph)", "Mock (Standalone)"],
        index=0 if _REAL_BACKEND_AVAILABLE else 1,
        horizontal=False,
        help="Real = the team's LangGraph orchestrator. Mock = Person 4's local mocks for fallback.",
        disabled=not _REAL_BACKEND_AVAILABLE,
        key="backend_mode_select",
    )
    if not _REAL_BACKEND_AVAILABLE:
        st.caption("⚠️ Real backend not importable — falling back to mocks.")

    st.divider()
    st.markdown("### 🤝 Team Ownership")
    st.markdown(
        """
        - **Person 1** · Orchestrator + Intent Agent
        - **Person 2** · Policy KB + Retrieval
        - **Person 3** · Mock APIs + Workflows
        - **Person 4** · UI + Product Advisory _(this app)_
        - **Person 5** · Risk + Evaluation
        """
    )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="se-header">
      <div class="se-header-left">
        <div class="se-logo">SE</div>
        <div>
          <div class="se-brand-name">ShopEase Support</div>
          <div class="se-brand-tag">Agentic AI · Capstone Prototype</div>
        </div>
      </div>
      <div class="se-header-badge">● Live Demo</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------

tab_chat, tab_compare, tab_about = st.tabs(
    ["💬 Customer Chat + Agent Console", "🛍️ Product Comparison", "ℹ️ About this demo"]
)


# =============================================================================
# TAB 1 — Customer Chat + Agent Console (side by side)
# =============================================================================

with tab_chat:
    # Split the page 40/60 so the busy agent console has more room.
    left, right = st.columns([0.40, 0.60], gap="large")

    # ----- LEFT: customer-facing chat ----------------------------------------
    with left:
        st.markdown('<div class="se-section-label">CUSTOMER VIEW</div>', unsafe_allow_html=True)
        st.markdown("#### Customer Chat")
        st.caption("What the shopper sees on the website or app.")

        # `container(height=...)` makes the chat scrollable inside a fixed box.
        chat_box = st.container(height=480, border=True)
        with chat_box:
            if not st.session_state.chat_history:
                st.info(
                    "👋 Hi! I'm ShopEase Assist. Ask me about an order, return, refund, "
                    "coupon, or product comparison. Or pick a demo scenario from the sidebar."
                )
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # The user can either type a message OR click the pre-filled scenario button.
        prefill = scenario["message"] if scenario["message"] else ""
        user_msg = st.chat_input("Type your message…")

        if prefill and not user_msg:
            preview = prefill[:60] + ("…" if len(prefill) > 60 else "")
            if st.button(
                f'▶️ Send scenario message: "{preview}"',
                use_container_width=True,
            ):
                user_msg = prefill

        # When a message comes in, run the full multi-agent pipeline and rerun.
        if user_msg:
            # 1. record the user's message
            st.session_state.chat_history.append({"role": "user", "content": user_msg})

            # 2. run the full multi-agent pipeline (this is the magic line)
            #    TODO: Person 1 — replace `run_full_pipeline` with the real
            #    orchestrator import once their LangGraph/CrewAI router lands.
            if backend_mode.startswith("Real") and _REAL_BACKEND_AVAILABLE:
                try:
                    state = run_real_pipeline(
                        query=user_msg,
                        order_id=order_id_input.strip() or None,
                        customer_id=customer_id_input.strip() or None,
                    )
                except Exception as e:
                    st.error(f"Real backend error — falling back to mocks: {e}")
                    state = run_full_pipeline(
                        query=user_msg,
                        order_id=order_id_input.strip() or None,
                    )
            else:
                state = run_full_pipeline(
                    query=user_msg,
                    order_id=order_id_input.strip() or None,
                )
            st.session_state.last_state = state

            # 3. record the assistant's reply
            st.session_state.chat_history.append({"role": "assistant", "content": state["response"]})
            st.rerun()

    # ----- RIGHT: agent-assist console ---------------------------------------
    with right:
        st.markdown('<div class="se-section-label">INTERNAL VIEW</div>', unsafe_allow_html=True)
        st.markdown("#### Agent Console")
        st.caption("What support agents and evaluators see while the AI is reasoning.")

        state = st.session_state.last_state
        if not state:
            st.warning("Send a customer message (or pick a scenario) to populate the console.")
        else:
            # All the agent panels go inside a single bordered container so the
            # console reads as one coherent dashboard during the demo.
            console_box = st.container(border=True)
            with console_box:
                render_intent_panel(state["intent"])
                st.divider()
                render_order_panel(state["order_context"])
                st.divider()
                render_policy_panel(state["policy"])
                st.divider()
                render_workflow_panel(state["workflow"])
                st.divider()
                render_risk_panel(state["risk"])
                st.divider()
                if state.get("product"):
                    render_product_comparison(state["product"])
                    st.divider()
                render_evaluation_panel(state["evaluation"], state["latency_ms"])
                st.divider()
                render_agent_trace(state["trace"])

                # Raw JSON audit log — hidden by default but available if asked.
                with st.expander("🪵 Raw audit log (JSON)"):
                    st.json(state)


# =============================================================================
# TAB 2 — Product Comparison
# =============================================================================
# This tab is Person 4's signature demo moment. It shows the Product Advisory
# Agent end-to-end: pick a category, pick two products, get a scored
# recommendation with a transparent explanation.

with tab_compare:
    st.markdown("### 🛍️ Product Advisory Agent")
    st.caption(
        "Person 4's signature agent — side-by-side comparison with "
        "scored recommendation and alternatives."
    )

    # Three columns: category picker, product A, product B.
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        category = st.selectbox("Category", pa.list_categories(), index=0)
    options = pa.list_products_by_category(category)
    with col_b:
        product_a = st.selectbox("Product A", options, index=0, key="prod_a")
    with col_c:
        idx_b = 1 if len(options) > 1 else 0
        product_b = st.selectbox("Product B", options, index=idx_b, key="prod_b")

    use_case = st.text_input(
        "Use case (optional)",
        value="College",
        help="e.g. College, Gaming, Photography, Travel — used to weight the recommendation.",
    )

    if product_a == product_b:
        st.warning("Pick two different products to compare.")
    else:
        if st.button("🔍 Compare", type="primary"):
            # Run the agent in forced-comparison mode.
            result = pa.compare(product_a, product_b, use_case=use_case or None)

            # Verdict at the top — this is the headline of the comparison.
            st.success(f"**Recommendation:** {result['recommendation']} — {result['reason']}")

            # Side-by-side spec table (with Processor as its own row now).
            st.markdown("#### Spec-by-spec comparison")
            table = pa.build_comparison_table(product_a, product_b)
            st.dataframe(table, use_container_width=True, hide_index=True)

            # Hidden scoring detail for the curious evaluator.
            with st.expander("How the recommendation was scored"):
                st.json(result["scores"])

            # In-stock alternatives, in case the customer wants more options.
            if result.get("alternatives"):
                st.markdown("#### Alternatives you might consider")
                st.dataframe(result["alternatives"], use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # Out-of-stock helper — separate section, lives below the comparison.
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown("#### 🔁 Out-of-stock helper")
    st.caption("Pick any product to see in-stock alternatives in the same category.")

    # Import here (rather than at the top) so this section is self-contained
    # — useful when teaching new readers what each block needs.
    import pandas as pd  # noqa: E402
    from modules.mock_agents import load_products  # noqa: E402

    full_df = load_products()
    target = st.selectbox("Check availability for:", full_df["name"].tolist())
    target_row = full_df[full_df["name"] == target].iloc[0]

    if target_row["in_stock"]:
        st.success(f"✅ {target} is in stock ({int(target_row['stock_qty'])} units available).")
    else:
        st.error(f"❌ {target} is currently out of stock.")
        alts = pa.find_alternatives(target)
        if alts:
            st.markdown("**Suggested alternatives in the same category:**")
            st.dataframe(pd.DataFrame(alts), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 3 — About / integration notes
# =============================================================================

with tab_about:
    st.markdown(
        """
        ### About this prototype

        This is **Person 4's** module for the ShopEase Agentic AI Capstone:
        the customer-facing chat, the support agent console, and the
        Product Advisory Agent.

        **Backend agents are mocked** (`modules/mock_agents.py`) so the
        UI can be demoed end-to-end without waiting for teammates.
        The mocks use the same input/output shapes the real agents will
        return, so swapping them in is a one-line change.

        #### Where teammates plug in

        | Real owner | What to replace | Function to swap |
        |---|---|---|
        | Person 1 | Orchestrator       | `run_full_pipeline()` |
        | Person 1 | Intent Agent       | `classify_intent()` |
        | Person 2 | Policy Retrieval   | `retrieve_policy()` |
        | Person 3 | Order Context      | `get_order_context()` |
        | Person 3 | Workflow Automation| `automate_workflow()` |
        | Person 5 | Escalation & Risk  | `assess_risk()` |
        | Person 5 | Evaluator          | `evaluate_response()` |

        Person 4 keeps owning `advise_products()` — that's the real agent
        in this module, not a mock.

        #### Demo scenarios covered

        - Order tracking with delay reason
        - Return request (eligible and non-eligible paths)
        - Damaged product → priority escalation
        - Lost high-value shipment → senior team
        - Coupon not applied → policy explanation
        - Product comparison (laptops, phones, headphones)
        - Invoice retrieval

        #### Success metrics this UI demonstrates

        - **Intent accuracy** — visible in the agent console
        - **Grounded responses** — policy reference is always shown
        - **Workflow completion** — action status shown per turn
        - **Escalation quality** — risk panel shows team + reason
        - **Agent productivity** — single console replaces 5+ tabs
        - **Response time** — `latency_ms` metric on every turn
        """
    )
