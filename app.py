"""
ShopEase Agentic AI Support — Streamlit Chat Interface

This is the entry point for Streamlit Cloud deployment.
Provides a customer chat interface that runs the full LangGraph pipeline.
"""

import streamlit as st
from src.orchestrator.graph import app
from src.utils.session import build_initial_state, generate_session_id

st.set_page_config(
    page_title="ShopEase AI Support",
    page_icon="🛒",
    layout="wide",
)

st.title("ShopEase AI Customer Support")
st.caption("Powered by Agentic AI — Multi-agent orchestration with LangGraph + GPT-4o")

with st.sidebar:
    st.header("Settings")
    customer_id = st.selectbox(
        "Customer ID",
        ["CUST_1001", "CUST_1002", "CUST_1003", "CUST_1004", "CUST_1005"],
        index=0,
    )
    channel = st.selectbox("Channel", ["web", "mobile", "email", "social"], index=0)

    st.divider()
    st.header("Quick Scenarios")
    scenarios = {
        "Order Tracking": "Where is my order SE10234? It was supposed to arrive yesterday.",
        "Return Request": "I want to return the running shoes I bought last week. They don't fit properly.",
        "Product Comparison": "Compare HP Pavilion and Lenovo IdeaPad laptop for college use.",
        "Damaged Product": "I received my Samsung Galaxy S24 with a cracked screen! This is a Rs 75000 phone and it arrived broken!",
        "Coupon Issue": "My coupon code SAVE20 is not working on my cart. Cart total is Rs 3500.",
        "Refund Status": "When will I get my refund? I returned my shoes 5 days ago.",
        "General FAQ": "What payment methods do you accept?",
    }
    selected_scenario = st.selectbox("Try a scenario:", ["(type your own)"] + list(scenarios.keys()))

if "session_id" not in st.session_state:
    st.session_state.session_id = generate_session_id()
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("metadata"):
            with st.expander("Agent Details"):
                st.json(msg["metadata"])

user_input = st.chat_input("How can I help you today?")

if selected_scenario != "(type your own)" and selected_scenario in scenarios:
    if st.sidebar.button("Send scenario message"):
        user_input = scenarios[selected_scenario]

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Processing through AI agents..."):
            state = build_initial_state(
                message=user_input,
                customer_id=customer_id,
                channel=channel,
                session_id=st.session_state.session_id,
            )
            result = app.invoke(state)

            response_text = result.get("response_text", "I'm sorry, I couldn't process that request.")
            st.write(response_text)

            if result.get("suggested_next_action"):
                st.info(f"{result['suggested_next_action']}")

            if result.get("references_cited"):
                st.caption(f"References: {', '.join(result['references_cited'])}")

            metadata = {
                "intent": result.get("intent"),
                "sentiment": result.get("sentiment"),
                "urgency": result.get("urgency"),
                "confidence": result.get("intent_confidence"),
                "risk_score": result.get("risk_score"),
                "risk_band": result.get("risk_band"),
                "escalation_required": result.get("escalation_required"),
                "target_team": result.get("target_team"),
                "quality_score": result.get("quality_score"),
                "agents_called": result.get("agents_called"),
            }

            with st.expander("View Agent Details (internal)"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    confidence = result.get("response_confidence", 0)
                    st.metric("Confidence", f"{confidence:.0%}")
                with col2:
                    st.metric("Intent", result.get("intent", "unknown"))
                with col3:
                    st.metric("Risk", f"{result.get('risk_score', 0):.2f}")

                st.json(metadata)

                if result.get("order_context"):
                    st.subheader("Order Context")
                    order = result["order_context"]
                    st.write(f"**Order:** {order.get('order_id')} | **Status:** {order.get('status')}")
                    if order.get("shipment"):
                        ship = order["shipment"]
                        st.write(f"**Carrier:** {ship.get('carrier')} | **Tracking:** {ship.get('tracking')} | **ETA:** {ship.get('eta')}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "metadata": metadata,
    })
