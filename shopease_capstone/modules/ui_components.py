"""
ui_components.py
================

Reusable Streamlit widgets for the ShopEase agent console.

Each `render_*` function takes one slice of the pipeline state and draws
one panel of the agent console. Keeping each panel in its own function
means app.py reads top-to-bottom like a storyboard, which makes the
demo easier to explain to evaluators.
"""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st


# -----------------------------------------------------------------------------
# Color maps — used by the small pill badges (Sentiment, Risk, Urgency).
# Green = good / safe, Amber = needs attention, Red = needs human now.
# -----------------------------------------------------------------------------

SENTIMENT_COLOR = {
    "Positive":   "#16a34a",
    "Neutral":    "#475569",
    "Frustrated": "#d97706",
    "Angry":      "#dc2626",
}

RISK_COLOR = {
    "None":   "#16a34a",
    "Low":    "#16a34a",
    "Medium": "#d97706",
    "High":   "#dc2626",
}

URGENCY_COLOR = {
    "Low":    "#475569",
    "Medium": "#d97706",
    "High":   "#dc2626",
}


def panel_heading(label: str, accent: str = "#F25C05") -> None:
    """Render a styled panel heading with a small colored accent bar.
    Used instead of emoji-prefixed markdown headings for a cleaner look.
    """
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:10px;margin:6px 0 10px 0;'>
          <div style='width:3px;height:18px;background:{accent};border-radius:2px;'></div>
          <div style='font-size:0.95rem;font-weight:700;color:#0F172A;
                      text-transform:uppercase;letter-spacing:0.04em;'>{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pill(text: str, color: str) -> str:
    """Return inline HTML for a small colored badge.

    Streamlit Markdown supports raw HTML if we pass `unsafe_allow_html=True`,
    so this is a cheap way to get colored status badges without extra libs.
    """
    return (
        f"<span style='background:{color};color:white;padding:3px 10px;"
        f"border-radius:12px;font-size:0.78rem;font-weight:600;'>{text}</span>"
    )


def render_metric_card(label: str, value: object, delta: str | None = None) -> None:
    """Render a metric-like card that allows long values to wrap."""
    delta_html = ""
    if delta:
        delta_html = f"<div class='se-metric-delta'>{escape(str(delta))}</div>"

    st.markdown(
        f"""
        <div class="se-metric-card">
          <div class="se-metric-label">{escape(str(label))}</div>
          <div class="se-metric-value">{escape(str(value))}</div>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Agent console panels
# =============================================================================

def render_intent_panel(intent_out: dict) -> None:
    """Top of the console: intent + sentiment + urgency at a glance."""
    panel_heading("Intent & Sentiment")

    def _label(text: str) -> str:
        return (
            f"<div style='font-size:0.72rem;color:#64748B;text-transform:uppercase;"
            f"letter-spacing:0.06em;font-weight:600;margin-bottom:6px;'>{text}</div>"
        )

    def _value(text: str) -> str:
        return (
            f"<div style='font-size:1.35rem;font-weight:700;color:#0F172A;"
            f"line-height:1.1;'>{text}</div>"
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(_label("Confidence"), unsafe_allow_html=True)
        st.markdown(_value(f"{intent_out['confidence']:.0%}"), unsafe_allow_html=True)
    with col2:
        st.markdown(_label("Sentiment"), unsafe_allow_html=True)
        st.markdown(
            pill(intent_out["sentiment"], SENTIMENT_COLOR.get(intent_out["sentiment"], "#475569")),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(_label("Urgency"), unsafe_allow_html=True)
        st.markdown(
            pill(intent_out["urgency"], URGENCY_COLOR.get(intent_out["urgency"], "#475569")),
            unsafe_allow_html=True,
        )
    if intent_out.get("keywords_matched"):
        st.caption("Keywords matched: " + ", ".join(intent_out["keywords_matched"]))


def render_order_panel(order_ctx: dict | None) -> None:
    """Show order details fetched by the Order Context Agent."""
    panel_heading("Order Context")
    if not order_ctx:
        st.info("No order ID detected in this conversation.")
        return
    o = order_ctx["raw"]
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Order:** {o['order_id']}")
        st.write(f"**Customer:** {o['customer_name']} ({o['customer_id']})")
        st.write(f"**Item:** {o['items'][0]['name']} (₹{o['items'][0]['price']:,})")
        st.write(f"**Total:** ₹{o['total_amount']:,}")
    with c2:
        st.write(f"**Shipment:** {o['shipment_status']}")
        st.write(f"**Carrier:** {o['carrier']} ({o['tracking_id']})")
        st.write(f"**Payment:** {o['payment_status']} ({o['payment_method']})")
        st.write(f"**ETA:** {o['expected_delivery']}")
    if o.get("delay_reason"):
        st.warning(f"Delay reason: {o['delay_reason']}")
    if o.get("issue_history"):
        with st.expander(f"Issue history ({len(o['issue_history'])})"):
            for issue in o["issue_history"]:
                st.write(f"- **{issue['date']}** — {issue['type']}: {issue['note']}")


def render_policy_panel(policy_out: dict | None) -> None:
    """Show which policy snippet grounded the answer."""
    panel_heading("Policy Reference")
    if not policy_out:
        st.info("No policy invoked for this query.")
        return
    st.write(
        f"**{policy_out['policy_id']} — {policy_out['title']}** "
        f"(_{policy_out['category']}, confidence {policy_out['confidence']:.2f}_)"
    )
    st.caption(policy_out["snippet"])


def render_workflow_panel(workflow_out: dict) -> None:
    """Show the action the Workflow Automation Agent took."""
    panel_heading("Workflow Action")
    status_color = {
        "Completed": "#16a34a", "Escalated": "#d97706", "Rejected": "#dc2626",
        "Pending":   "#475569", "Skipped":   "#94a3b8",
    }.get(workflow_out["status"], "#475569")
    st.markdown(
        f"**Action:** `{workflow_out['action']}` &nbsp; "
        + pill(workflow_out["status"], status_color),
        unsafe_allow_html=True,
    )
    st.caption(workflow_out["detail"])
    if workflow_out.get("ticket_id"):
        st.code(f"Ticket: {workflow_out['ticket_id']}", language="text")


def render_risk_panel(risk_out: dict) -> None:
    """Show the Escalation & Risk Agent's verdict and routing decision."""
    panel_heading("Risk & Escalation", accent="#DC2626")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("Risk Level")
        st.markdown(
            pill(risk_out["risk_level"], RISK_COLOR.get(risk_out["risk_level"], "#475569")),
            unsafe_allow_html=True,
        )
        st.caption(f"Risk score: {risk_out['risk_score']}")
    with c2:
        if risk_out["escalate"]:
            st.markdown(f"**Escalated to:** {risk_out['target_team']}")
        else:
            st.markdown("**Escalated to:** _no escalation_")
    st.write("**Reasons**")
    for r in risk_out["reasons"]:
        st.write(f"- {r}")


def render_evaluation_panel(eval_out: dict, latency_ms: int) -> None:
    """Show the evaluator's score for this turn — Person 5 owns this in real."""
    panel_heading("Evaluator Score")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card("Quality Score", f"{eval_out['score']}/100")
    with c2:
        render_metric_card("Verdict", eval_out["verdict"])
    with c3:
        render_metric_card("Latency", f"{latency_ms} ms")
    with st.expander("Score breakdown"):
        for n in eval_out["notes"]:
            st.write(f"- {n}")


def render_agent_trace(trace: list[dict]) -> None:
    """Render the 'this system is truly agentic' table.

    One row per agent, showing the owner and a short preview of what it
    contributed. This is the panel that proves to evaluators that we have
    a multi-agent system and not a single chatbot prompt.
    """
    panel_heading("Agent Trace")
    rows = []
    for step in trace:
        out = step["output"]
        if isinstance(out, dict):
            preview = ", ".join(
                f"{k}={v}" for k, v in list(out.items())[:2]
                if not isinstance(v, (dict, list))
            )
        else:
            preview = str(out)
        rows.append({
            "Agent":  step["agent"],
            "Owner":  step["owner"],
            "Output (preview)": preview[:120] if preview else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_product_comparison(product_out: dict) -> None:
    """Render an inline product comparison card inside the agent console.

    Used when the customer asks a product question in chat (Mode = "comparison"
    or "recommendation"). The dedicated Product Comparison tab uses richer
    widgets — this is just a compact summary card.
    """
    if not product_out or product_out["mode"] == "none":
        return

    panel_heading("Product Advisory")

    if product_out["mode"] == "comparison":
        a, b = product_out["products"]
        c1, c2 = st.columns(2)
        for col, p in zip((c1, c2), (a, b)):
            with col:
                tag = " ✅ Recommended" if p["name"] == product_out["recommendation"] else ""
                st.markdown(f"**{p['name']}**{tag}")
                st.caption(f"{p['brand']} • {p.get('processor', 'N/A')} • ₹{p['price_inr']:,} • {p['rating']}★")
                st.write(f"RAM {p['ram_gb']}GB · Storage {p['storage_gb']}GB · Battery {p['battery_hours']}h")
                st.write(f"In stock: {'Yes' if p['in_stock'] else 'No'}")
        st.success(f"**Recommendation:** {product_out['recommendation']} — {product_out['reason']}")

    elif product_out["mode"] == "recommendation":
        st.success(f"**Recommendation:** {product_out['recommendation']} — {product_out['reason']}")

    if product_out.get("alternatives"):
        with st.expander("Alternatives you might consider"):
            st.dataframe(pd.DataFrame(product_out["alternatives"]),
                         use_container_width=True, hide_index=True)
