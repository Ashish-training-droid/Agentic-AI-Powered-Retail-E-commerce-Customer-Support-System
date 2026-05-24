"""
mock_agents.py
==============

This file simulates the 7 AI agents from the ShopEase capstone architecture.

WHY MOCK?
---------
The other teammates (Persons 1, 2, 3, 5) are still building their real agents
in parallel. Person 4 (UI) can't wait for them, so we build mock versions that
behave like the real ones — same inputs, same outputs — and the UI talks to
these mocks. When the real agents land, we swap the implementation behind
each function and the UI keeps working.

PUBLIC FUNCTIONS (these are the ones the UI calls):
  classify_intent(query)                -> dict
  get_order_context(order_id, query)    -> dict | None
  retrieve_policy(intent, query)        -> dict | None
  automate_workflow(intent, order_ctx)  -> dict
  assess_risk(query, intent_out, order_ctx) -> dict
  generate_response(query, agent_outputs)   -> str
  evaluate_response(agent_outputs)      -> dict
  run_full_pipeline(query, ...)         -> dict   # convenience: runs all 7

WHO OWNS WHAT IN THE REAL PROJECT (search for "TODO: Person X" below):
  Person 1 -> classify_intent + run_full_pipeline (orchestrator)
  Person 2 -> retrieve_policy + the policy KB in data/policies.json
  Person 3 -> get_order_context + automate_workflow + data/orders.json
  Person 4 -> product advisory (lives in product_advisory.py) + the UI
  Person 5 -> assess_risk + evaluate_response
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any

import pandas as pd

# Hook into the real backend (LangGraph pipeline owned by Person 1)
import sys
import os as _os

_REPO_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.orchestrator.graph import app as _real_graph_app
    _REAL_BACKEND_AVAILABLE = True
    _BACKEND_IMPORT_ERROR = ""
except Exception as _e:
    _real_graph_app = None
    _REAL_BACKEND_AVAILABLE = False
    _BACKEND_IMPORT_ERROR = str(_e)

# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
# All three mock data files live in ../data/ relative to this module.
# When real APIs are available, point these loaders at HTTP endpoints instead.

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)


def load_orders() -> dict[str, dict[str, Any]]:
    """Load mock orders from data/orders.json.
    TODO: Person 3 — replace with a call to the real Order Management mock API.
    """
    with open(os.path.join(DATA_DIR, "orders.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_policies() -> dict[str, dict[str, Any]]:
    """Load mock policy snippets from data/policies.json.
    TODO: Person 2 — replace with the real RAG policy retriever output.
    """
    with open(os.path.join(DATA_DIR, "policies.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_products() -> pd.DataFrame:
    """Load mock product catalog from data/products.csv.
    TODO: Person 2 — point at the real product catalog source when ready.
    """
    return pd.read_csv(os.path.join(DATA_DIR, "products.csv"))


# =============================================================================
# AGENT 1 — INTENT CLASSIFICATION                          (real owner: Person 1)
# =============================================================================
# A real Intent Classifier would be an LLM call or a fine-tuned model.
# For the demo we use simple keyword matching — easy to explain, deterministic.

# Each intent has a list of keywords. If the customer message contains any of
# these keywords, that intent gets a "vote". The intent with most votes wins.
INTENT_KEYWORDS = {
    "Order Tracking":   ["where", "track", "delivery", "shipped", "arrive", "eta", "out for delivery"],
    "Return Request":   ["return", "send back", "give back", "exchange"],
    "Refund Status":    ["refund", "money back", "credited", "settlement"],
    "Damaged Product":  ["damaged", "broken", "cracked", "defective", "not working", "doa"],
    "Lost Shipment":    ["lost", "missing", "never arrived", "not delivered", "no update"],
    "Coupon Issue":     ["coupon", "promo", "discount code", "voucher", "festive10"],
    "Product Inquiry":  ["compare", "which is better", "recommend", "suggest", "vs", "difference",
                          "best laptop", "best phone"],
    "Invoice Request":  ["invoice", "bill", "receipt", "gst"],
    "Payment Issue":    ["payment failed", "double charged", "deducted twice", "not paid"],
}

# When two intents tie on keyword count, prefer the more specific one. Example:
# "My headphones arrived cracked!" matches both 'arrive' (Order Tracking) and
# 'cracked' (Damaged Product). Damaged Product should win.
SPECIFIC_INTENT_PRIORITY = [
    "Damaged Product", "Lost Shipment", "Payment Issue", "Coupon Issue",
    "Refund Status", "Return Request", "Invoice Request", "Product Inquiry",
    "Order Tracking", "General Inquiry",
]

# Words that strongly signal a frustrated or angry customer.
NEGATIVE_SENTIMENT_WORDS = [
    "angry", "frustrated", "disappointed", "useless", "worst", "terrible",
    "horrible", "pathetic", "fraud", "cheat", "scam", "fed up", "complaint",
    "never again", "refund now", "ridiculous", "unacceptable", "appalling",
    "hate", "broken promise",
]


def classify_intent(query: str) -> dict[str, Any]:
    """Detect intent, sentiment, urgency and confidence from the customer message.

    Returns a dictionary the UI can render directly:
        {
          "intent":      str,    # e.g. "Order Tracking"
          "confidence":  float,  # 0.0–1.0
          "sentiment":   str,    # "Positive" / "Neutral" / "Frustrated" / "Angry"
          "urgency":     str,    # "Low" / "Medium" / "High"
          "keywords_matched": list[str]
        }
    """
    msg = query.lower().strip()

    # --- Step 1: score every intent by counting keyword matches ---------------
    scored: list[tuple[str, int, list[str]]] = []
    for intent_name, keywords in INTENT_KEYWORDS.items():
        matched_keywords = [kw for kw in keywords if kw in msg]
        if matched_keywords:
            scored.append((intent_name, len(matched_keywords), matched_keywords))

    # --- Step 2: pick the winning intent --------------------------------------
    if scored:
        # Primary sort: more keyword hits wins. Tie-breaker: specificity ranking.
        priority_rank = {name: i for i, name in enumerate(SPECIFIC_INTENT_PRIORITY)}
        scored.sort(key=lambda x: (-x[1], priority_rank.get(x[0], 99)))
        intent, hits, matched = scored[0]
        # Confidence: 0.55 baseline, +0.15 per matched keyword, capped at 0.97.
        confidence = min(0.55 + 0.15 * hits, 0.97)
    else:
        # No keywords matched — fall back to a low-confidence general intent.
        intent, matched, confidence = "General Inquiry", [], 0.45

    # --- Step 3: detect sentiment ---------------------------------------------
    neg_hits = sum(1 for w in NEGATIVE_SENTIMENT_WORDS if w in msg)
    has_exclaim = "!" in query
    if neg_hits >= 2 or "!!" in query or (query.isupper() and len(query) > 5):
        sentiment = "Angry"
    elif neg_hits >= 1 or (has_exclaim and intent in {"Damaged Product", "Lost Shipment", "Payment Issue"}):
        sentiment = "Frustrated"
    elif any(w in msg for w in ["thanks", "great", "love", "awesome"]):
        sentiment = "Positive"
    else:
        sentiment = "Neutral"

    # --- Step 4: derive urgency from intent + sentiment -----------------------
    if intent in {"Lost Shipment", "Damaged Product", "Payment Issue"} or sentiment == "Angry":
        urgency = "High"
    elif intent in {"Refund Status", "Return Request", "Coupon Issue"}:
        urgency = "Medium"
    else:
        urgency = "Low"

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "sentiment": sentiment,
        "urgency": urgency,
        "keywords_matched": matched,
    }


# =============================================================================
# AGENT 2 — ORDER CONTEXT                                  (real owner: Person 3)
# =============================================================================
# In production this would call multiple back-end APIs (Order Mgmt, Payment,
# Logistics, CRM) and merge the results. For the demo we just read one JSON file.

# Regex to spot order IDs like "SE10234" inside a free-text customer message.
ORDER_ID_REGEX = re.compile(r"\b(SE\d{5,})\b", re.IGNORECASE)


def get_order_context(order_id: str | None = None, query: str = "") -> dict[str, Any] | None:
    """Look up order details from mock data.

    Either pass an explicit order_id, or pass the customer query and we'll
    extract an order ID from the text. Returns None if no order is found.

    Returns:
        {
          "order_id":      str,
          "customer_id":   str,
          "customer_name": str,
          "summary":       str,    # one-line human-readable summary
          "raw":           dict,   # full order record (for detail panels)
        }
    """
    orders = load_orders()

    # Prefer the order ID in the latest customer message. This avoids a stale
    # sidebar Order ID overriding a demo scenario like "Order SE10236".
    if query:
        match = ORDER_ID_REGEX.search(query)
        if match:
            order_id = match.group(1).upper()

    if not order_id or order_id not in orders:
        return None

    o = orders[order_id]
    summary = (
        f"Order {o['order_id']} placed on {o['order_date']} by {o['customer_name']}. "
        f"Item: {o['items'][0]['name']} (₹{o['items'][0]['price']}). "
        f"Payment: {o['payment_status']} via {o['payment_method']}. "
        f"Shipment: {o['shipment_status']} (carrier {o['carrier']}, tracking {o['tracking_id']}). "
        f"ETA: {o['expected_delivery']}."
    )

    return {
        "order_id": o["order_id"],
        "customer_id": o["customer_id"],
        "customer_name": o["customer_name"],
        "summary": summary,
        "raw": o,
    }


# =============================================================================
# AGENT 3 — POLICY RETRIEVAL                               (real owner: Person 2)
# =============================================================================
# Real implementation: chunk the policy documents, embed them, and do RAG.
# Demo implementation: hard-coded map from intent -> policy ID, plus a couple
# of special-case overrides (e.g. mentions of "FESTIVE10" coupon).

INTENT_TO_POLICY = {
    "Return Request":   "RETURN-001",
    "Damaged Product":  "RETURN-002",
    "Refund Status":    "REFUND-001",
    "Lost Shipment":    "DELIVERY-001",
    "Coupon Issue":     "COUPON-001",
    "Invoice Request":  "RETURN-001",  # closest applicable rule
}


def retrieve_policy(intent: str, query: str = "") -> dict[str, Any] | None:
    """Return the most relevant policy snippet for the given intent.

    Returns:
        {
          "policy_id":  str,
          "title":      str,
          "snippet":    str,    # the actual policy text to ground the answer
          "category":   str,
          "confidence": float,
        }
    """
    policies = load_policies()
    msg = query.lower()

    # Special-case: if the customer mentioned a specific coupon code, use the
    # coupon-specific policy instead of the generic one.
    if "festive10" in msg:
        p = policies["COUPON-FESTIVE10"]
    else:
        policy_id = INTENT_TO_POLICY.get(intent)
        if not policy_id:
            return None
        p = policies[policy_id]

    return {
        "policy_id": p["policy_id"],
        "title": p["title"],
        "snippet": p["rule"],
        "category": p["category"],
        "confidence": 0.88,  # mock confidence — real retriever returns a real score
    }


# =============================================================================
# AGENT 5 — WORKFLOW AUTOMATION                            (real owner: Person 3)
# =============================================================================
# Performs the actual "do something" step: track a shipment, create a return
# request, generate an invoice, raise an escalation ticket, etc.

def automate_workflow(intent: str, order_ctx: dict | None) -> dict[str, Any]:
    """Run the self-service workflow that matches the detected intent.

    Returns:
        {
          "action":     str,    # e.g. "create_return_request"
          "status":     str,    # "Completed" / "Escalated" / "Rejected" / "Skipped" / "Pending"
          "ticket_id":  str|None,
          "detail":     str,    # human-readable description of what happened
          "timestamp":  str,
        }
    """
    # If we don't even have an order, most workflows can't run.
    if not order_ctx:
        return {"action": "None", "status": "Skipped",
                "ticket_id": None, "detail": "No order context available.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    o = order_ctx["raw"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Each branch below maps one intent to one mock workflow.
    if intent == "Order Tracking":
        return {
            "action": "track_shipment", "status": "Completed", "ticket_id": None,
            "detail": f"Latest carrier scan shows: {o['shipment_status']}. ETA {o['expected_delivery']}.",
            "timestamp": ts,
        }

    if intent == "Return Request":
        if o["return_eligible"]:
            return {
                "action": "create_return_request", "status": "Completed",
                "ticket_id": f"RET-{o['order_id'][2:]}",
                "detail": f"Return initiated for {o['items'][0]['name']}. Pickup will be scheduled in 1-2 business days.",
                "timestamp": ts,
            }
        return {
            "action": "create_return_request", "status": "Rejected", "ticket_id": None,
            "detail": "Order is outside the return window or marked non-returnable.",
            "timestamp": ts,
        }

    if intent == "Refund Status":
        return {
            "action": "get_refund_status", "status": "Completed", "ticket_id": None,
            "detail": "No refund currently in queue for this order. Standard refunds settle in 5-7 business days post quality check.",
            "timestamp": ts,
        }

    if intent == "Invoice Request":
        return {
            "action": "get_invoice",
            "status": "Completed" if o["invoice_available"] else "Pending",
            "ticket_id": None,
            "detail": "Invoice ready for download." if o["invoice_available"] else "Invoice is being generated.",
            "timestamp": ts,
        }

    if intent in ("Damaged Product", "Lost Shipment"):
        # These always require a human ticket — workflow creates the ticket
        # and the Risk Agent will route it to the right team.
        return {
            "action": "create_ticket", "status": "Escalated",
            "ticket_id": f"ESC-{o['order_id'][2:]}",
            "detail": f"Specialist ticket created for {intent}. Routed to relevant team.",
            "timestamp": ts,
        }

    if intent == "Coupon Issue":
        return {
            "action": "check_coupon_eligibility", "status": "Completed", "ticket_id": None,
            "detail": "Coupon eligibility checked against current cart and offer terms.",
            "timestamp": ts,
        }

    # Default: no workflow runs.
    return {"action": "None", "status": "Skipped", "ticket_id": None,
            "detail": "No automated workflow for this intent.", "timestamp": ts}


# =============================================================================
# AGENT 6 — ESCALATION & RISK                              (real owner: Person 5)
# =============================================================================
# Rule-based risk scoring: add points for each red flag, then bucket the total.

def assess_risk(query: str, intent_out: dict, order_ctx: dict | None) -> dict[str, Any]:
    """Decide whether this case needs human escalation and to whom.

    Returns:
        {
          "risk_level":  "None" | "Low" | "Medium" | "High",
          "risk_score":  int,
          "escalate":    bool,
          "target_team": str | None,
          "reasons":     list[str],
        }
    """
    risk_score = 0
    reasons: list[str] = []

    # --- Sentiment-based risk -------------------------------------------------
    if intent_out["sentiment"] == "Angry":
        risk_score += 3; reasons.append("Angry customer sentiment")
    elif intent_out["sentiment"] == "Frustrated":
        risk_score += 1; reasons.append("Frustrated tone")

    # --- Confidence-based risk ------------------------------------------------
    # Low intent confidence means the AI isn't sure — safer to escalate.
    if intent_out["confidence"] < 0.6:
        risk_score += 2; reasons.append("Low intent confidence")

    # --- Intent-based risk ----------------------------------------------------
    intent = intent_out["intent"]
    if intent in {"Lost Shipment", "Payment Issue"}:
        risk_score += 3; reasons.append(f"High-impact intent: {intent}")
    elif intent == "Damaged Product":
        risk_score += 2; reasons.append("Damaged product report")

    # --- Order-value-based risk -----------------------------------------------
    if order_ctx and order_ctx["raw"]["total_amount"] >= 50000:
        risk_score += 2; reasons.append("High-value order (≥ ₹50,000)")

    # --- Shipment-status-based risk -------------------------------------------
    if order_ctx and order_ctx["raw"]["shipment_status"] == "Lost in Transit":
        risk_score += 3; reasons.append("Shipment marked lost by carrier")

    # --- Bucket the total score into a level ----------------------------------
    if risk_score >= 5:
        level, escalate = "High", True
    elif risk_score >= 3:
        level, escalate = "Medium", True
    elif risk_score >= 1:
        level, escalate = "Low", False
    else:
        level, escalate = "None", False

    # Map the intent to the right specialist team if we're escalating.
    team_map = {
        "Lost Shipment":   "Logistics + Senior Agent",
        "Damaged Product": "Replacement Team",
        "Payment Issue":   "Payments Specialist",
        "Refund Status":   "Refund Specialist",
    }
    target_team = team_map.get(intent, "Senior Support Agent") if escalate else None

    return {
        "risk_level": level,
        "risk_score": risk_score,
        "escalate": escalate,
        "target_team": target_team,
        "reasons": reasons or ["No risk factors detected"],
    }


# =============================================================================
# AGENT 7 — RESPONSE GENERATION                           (owner: Person 1 + 4)
# =============================================================================
# Takes the outputs of every other agent and writes the final customer reply.
# A real implementation would call an LLM with a carefully designed prompt.
# Our mock uses one templated branch per intent — boring but easy to demo.

def generate_response(query: str, agent_outputs: dict) -> str:
    """Compose the final customer-facing reply.

    `agent_outputs` should contain the outputs of the other agents:
        {
          "intent":   dict from classify_intent(),
          "order":    dict from get_order_context() (or None),
          "policy":   dict from retrieve_policy() (or None),
          "workflow": dict from automate_workflow(),
          "risk":     dict from assess_risk(),
          "product":  dict from product_advisory() (or None),
        }
    Returns: plain markdown string ready to display in the chat panel.
    """
    intent_out = agent_outputs["intent"]
    order_ctx  = agent_outputs.get("order")
    policy_out = agent_outputs.get("policy")
    workflow   = agent_outputs["workflow"]
    risk       = agent_outputs["risk"]
    product    = agent_outputs.get("product")

    name = order_ctx["customer_name"] if order_ctx else "there"
    intent = intent_out["intent"]
    parts: list[str] = [f"Hi {name}, thanks for reaching out to ShopEase Support."]

    # One templated reply per intent. The goal is to ground each reply in
    # real order data and the policy snippet so the answer is consistent.

    if intent == "Order Tracking" and order_ctx:
        o = order_ctx["raw"]
        line = (f"Your order {o['order_id']} ({o['items'][0]['name']}) is currently "
                f"**{o['shipment_status']}** with {o['carrier']} (tracking {o['tracking_id']}). "
                f"Expected delivery: {o['expected_delivery']}.")
        if o["delay_reason"]:
            line += f" Heads up — there is a delay due to: {o['delay_reason']}."
        parts.append(line)

    elif intent == "Return Request" and order_ctx:
        if workflow["status"] == "Completed":
            parts.append(
                f"I've initiated a return for **{order_ctx['raw']['items'][0]['name']}**. "
                f"Pickup will be arranged within 1-2 business days. "
                f"Your reference is {workflow['ticket_id']}."
            )
        else:
            parts.append("Unfortunately this order is outside our return window or marked non-returnable.")
        if policy_out:
            parts.append(f"> 📘 **Policy reference — {policy_out['title']}**\n>\n> {policy_out['snippet']}")

    elif intent == "Refund Status":
        parts.append(workflow["detail"])
        if policy_out:
            parts.append(f"> 📘 **Policy reference — {policy_out['title']}**\n>\n> {policy_out['snippet']}")

    elif intent == "Damaged Product" and order_ctx:
        parts.append(
            f"I'm really sorry your **{order_ctx['raw']['items'][0]['name']}** arrived damaged. "
            f"I've raised a priority ticket ({workflow.get('ticket_id', 'TBD')}) and our Replacement Team "
            f"will reach you within 24 hours."
        )
        if policy_out:
            parts.append(f"> 📘 **Policy reference — {policy_out['title']}**\n>\n> {policy_out['snippet']}")

    elif intent == "Lost Shipment" and order_ctx:
        parts.append(
            f"I can see your order {order_ctx['raw']['order_id']} hasn't moved since the carrier's last scan. "
            f"Given the value of this shipment, I've escalated it to our Logistics + Senior Agent team "
            f"(ticket {workflow.get('ticket_id', 'TBD')})."
        )
        if policy_out:
            parts.append(f"> 📘 **Policy reference — {policy_out['title']}**\n>\n> {policy_out['snippet']}")

    elif intent == "Coupon Issue":
        parts.append(workflow["detail"])
        if policy_out:
            parts.append(f"> 📘 **Policy reference — {policy_out['title']}**\n>\n> {policy_out['snippet']}")

    elif intent == "Invoice Request" and order_ctx:
        parts.append(workflow["detail"])

    elif intent == "Product Inquiry" and product:
        if product["mode"] == "comparison":
            a, b = product["products"]
            parts.append(
                f"Comparing **{a['name']}** vs **{b['name']}** — my pick is **{product['recommendation']}**. "
                f"{product['reason']}"
            )
        elif product["mode"] == "recommendation":
            parts.append(f"My top pick is **{product['recommendation']}**. {product['reason']}")
        if product.get("alternatives"):
            alt_names = ", ".join(a["name"] for a in product["alternatives"][:2])
            parts.append(f"You might also like: {alt_names}.")

    else:
        # Fallback when we can't match a confident intent or we lack context.
        parts.append("Could you share your order ID or a bit more detail so I can help you faster?")

    # Add an escalation note if the Risk Agent flagged this case.
    if risk["escalate"]:
        parts.append(
            f"_This case has been flagged as **{risk['risk_level']}** priority "
            f"and routed to {risk['target_team']} for human follow-up._"
        )

    parts.append("_Is there anything else I can help you with?_")
    return "\n\n".join(parts)


# =============================================================================
# EVALUATOR                                                (real owner: Person 5)
# =============================================================================
# Simple rubric: 25 points each for intent confidence, policy grounding,
# workflow execution, and risk handling. The UI shows this number prominently
# so evaluators in the demo can see "the AI is grading itself".

def evaluate_response(agent_outputs: dict) -> dict[str, Any]:
    """Score the AI's overall handling of this turn out of 100."""
    intent_out = agent_outputs["intent"]
    policy_out = agent_outputs.get("policy")
    workflow   = agent_outputs["workflow"]
    risk       = agent_outputs["risk"]

    score = 0
    notes: list[str] = []

    # +25 if intent is detected confidently
    if intent_out["confidence"] >= 0.75:
        score += 25; notes.append("Intent confidence high")
    elif intent_out["confidence"] >= 0.6:
        score += 15; notes.append("Intent confidence medium")
    else:
        notes.append("Intent confidence low")

    # +25 if the response is grounded in an approved policy
    if policy_out:
        score += 25; notes.append("Response grounded in policy")

    # +25 if a workflow actually ran (or was correctly escalated)
    if workflow["status"] in {"Completed", "Escalated"}:
        score += 25; notes.append(f"Workflow {workflow['status'].lower()}")

    # +25 if risk was handled: either no risk detected, or correctly escalated
    if risk["risk_level"] == "None" or risk["escalate"]:
        score += 25; notes.append("Risk handled correctly")

    # Translate the numeric score into a 4-bucket verdict.
    if score >= 85:
        verdict = "Excellent"
    elif score >= 65:
        verdict = "Good"
    elif score >= 45:
        verdict = "Acceptable"
    else:
        verdict = "Needs Review"

    return {"score": score, "verdict": verdict, "notes": notes}


# =============================================================================
# ORCHESTRATOR WRAPPER                                      (real owner: Person 1)
# =============================================================================
# Runs all 7 agents in sequence and packages the results into a single state
# object the UI can render. Person 1 will replace this with a real router
# (LangGraph / CrewAI / custom) — but the return shape must stay the same.

def run_full_pipeline(
    query: str,
    order_id: str | None = None,
    product_a: str | None = None,
    product_b: str | None = None,
    use_case: str | None = None,
) -> dict[str, Any]:
    """Run the full multi-agent pipeline and return everything for the UI."""
    # Import here to avoid a circular import (product_advisory uses load_products).
    from .product_advisory import advise_products

    start = time.time()

    # Step 1: figure out what the customer wants.
    intent_out = classify_intent(query)

    # Step 2: look up their order, if any.
    order_ctx = get_order_context(order_id, query)

    # Step 3: find the relevant policy snippet.
    policy_out = retrieve_policy(intent_out["intent"], query)

    # Step 4: if it's a product question, run product advisory.
    product_out = None
    if intent_out["intent"] == "Product Inquiry" or product_a or product_b:
        product_out = advise_products(query, product_a, product_b, use_case)

    # Step 5: run the workflow action (track / return / refund / ticket / ...).
    workflow_out = automate_workflow(intent_out["intent"], order_ctx)

    # Step 6: assess risk and decide on escalation.
    risk_out = assess_risk(query, intent_out, order_ctx)

    # Step 7: generate the final customer-facing reply.
    response_text = generate_response(query, {
        "intent": intent_out, "order": order_ctx, "policy": policy_out,
        "workflow": workflow_out, "risk": risk_out, "product": product_out,
    })

    # Evaluator scores everything we just did.
    eval_out = evaluate_response({
        "intent": intent_out, "policy": policy_out,
        "workflow": workflow_out, "risk": risk_out,
    })

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "query":         query,
        "intent":        intent_out,
        "order_context": order_ctx,
        "policy":        policy_out,
        "product":       product_out,
        "workflow":      workflow_out,
        "risk":          risk_out,
        "response":      response_text,
        "evaluation":    eval_out,
        "latency_ms":    elapsed_ms,
        # The "trace" is what makes the system look agentic in the demo:
        # one row per agent showing what each contributed.
        "trace": [
            {"agent": "Intent Classification", "owner": "Person 1",     "output": intent_out},
            {"agent": "Order Context",         "owner": "Person 3",     "output": order_ctx},
            {"agent": "Policy Retrieval",      "owner": "Person 2",     "output": policy_out},
            {"agent": "Product Advisory",      "owner": "Person 4",     "output": product_out},
            {"agent": "Workflow Automation",   "owner": "Person 3",     "output": workflow_out},
            {"agent": "Escalation & Risk",     "owner": "Person 5",     "output": risk_out},
            {"agent": "Response Generation",   "owner": "Person 1 + 4",
             "output": {"response_preview": response_text[:120] + "..."}},
        ],
    }


# =============================================================================
# REAL BACKEND ADAPTER  (calls Person 1's LangGraph instead of the mocks above)
# =============================================================================
# Field-mapping based on confirmed responses from `app.invoke()` across 7 demo
# scenarios. Tested against the actual backend output, not guessed.

def _intent_title(s: str) -> str:
    """Convert their lowercase_underscore intent to Title Case for the UI."""
    return s.replace("_", " ").title() if s else "Unknown"


def _sentiment_title(s: str) -> str:
    """Their backend uses lowercase ('angry'); UI shows ('Angry').
    Also maps 'negative' -> 'Frustrated' to match the UI's color scheme."""
    return {
        "positive":   "Positive",
        "neutral":    "Neutral",
        "negative":   "Frustrated",
        "angry":      "Angry",
    }.get(s, "Neutral")


def _urgency_title(u: str) -> str:
    """Their backend has 'critical' which UI doesn't render — map to High."""
    return {
        "low":      "Low",
        "medium":   "Medium",
        "high":     "High",
        "critical": "High",
    }.get(u, "Low")


def _risk_level_from_score(score: float) -> str:
    """Bucket their float risk_score (0.0-1.0) into the UI's four levels."""
    if score >= 0.7: return "High"
    if score >= 0.4: return "Medium"
    if score >= 0.15: return "Low"
    return "None"


def _verdict_from_quality(q: float) -> str:
    if q >= 0.85: return "Excellent"
    if q >= 0.65: return "Good"
    if q >= 0.45: return "Acceptable"
    return "Needs Review"


def _adapt_order_context(raw_oc: dict, customer_id: str) -> dict | None:
    """Translate their order_context shape to your UI's expected shape."""
    if not raw_oc:
        return None

    items = raw_oc.get("items") or [{"name": "Item", "price": 0, "qty": 1}]
    payment = raw_oc.get("payment") or {}
    shipment = raw_oc.get("shipment") or {}

    return {
        "order_id":      raw_oc.get("order_id", "N/A"),
        "customer_id":   customer_id,
        "customer_name": "Customer " + customer_id.replace("CUST_", "").lstrip("0") if customer_id else "Customer",
        "summary":       f"Order {raw_oc.get('order_id', 'N/A')} — {raw_oc.get('status', 'unknown')}",
        "raw": {
            "order_id":          raw_oc.get("order_id", "N/A"),
            "customer_id":       customer_id,
            "customer_name":     "Customer " + customer_id.replace("CUST_", "").lstrip("0") if customer_id else "Customer",
            "order_date":        shipment.get("delivered_on") or "N/A",
            "items":             items,
            "total_amount":      payment.get("amount", 0),
            "payment_status":    "Paid" if payment.get("status") == "captured" else (payment.get("status") or "N/A"),
            "payment_method":    payment.get("method", "N/A"),
            "shipment_status":   (shipment.get("status") or "N/A").replace("_", " ").title(),
            "carrier":           shipment.get("carrier", "N/A"),
            "tracking_id":       shipment.get("tracking", "N/A"),
            "expected_delivery": shipment.get("eta") or shipment.get("delivered_on") or "N/A",
            "delay_reason":      None,
            "invoice_available": True,
            "return_eligible":   raw_oc.get("status") == "delivered",
            "issue_history":     [{"date": "—", "type": "CRM Note", "note": n}
                                  for n in (raw_oc.get("crm_notes") or [])],
        },
    }


def _adapt_policy(snippets: list[dict] | None) -> dict | None:
    if not snippets:
        return None
    top = snippets[0]
    return {
        "policy_id":  top.get("reference_id", "N/A"),
        "title":      top.get("explanation", "Relevant Policy")[:80] or "Policy",
        "snippet":    top.get("rule", ""),
        "category":   "Policy",
        "confidence": float(top.get("confidence", 0.85)),
    }


def _adapt_workflow(action_taken: str | None, action_result: dict | None,
                    escalation_required: bool) -> dict:
    ar = action_result or {}
    if not action_taken and not escalation_required:
        return {"action": "None", "status": "Skipped",
                "ticket_id": None, "detail": "No automated action taken.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    if escalation_required:
        status = "Escalated"
    elif ar.get("success"):
        status = "Completed"
    else:
        status = "Pending"

    return {
        "action":     action_taken or "escalate",
        "status":     status,
        "ticket_id":  ar.get("return_id") or ar.get("ticket_id"),
        "detail":     ar.get("message") or ar.get("details", "Action processed."),
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _adapt_risk(risk_score: float, escalation_required: bool,
                escalation_reason: str, target_team: str) -> dict:
    return {
        "risk_level":  _risk_level_from_score(risk_score),
        "risk_score":  risk_score,
        "escalate":    escalation_required,
        "target_team": target_team or None,
        "reasons":     [escalation_reason] if escalation_reason else
                       ([f"Risk score {risk_score:.2f}"] if risk_score > 0.15 else
                        ["No risk factors detected"]),
    }


def _adapt_trace(agents_called: list[str], audit_trail: list[dict]) -> list[dict]:
    """Build the agent trace table. Match each called agent with its audit entry."""
    owner_map = {
        "intent_classifier":   "Person 1",
        "order_context":       "Person 3",
        "policy_retrieval":    "Person 2",
        "product_advisory":    "Person 4",
        "workflow_automation": "Person 3",
        "escalation_risk":     "Person 5",
        "evaluator":           "Person 5",
        "response_generator":  "Person 1 + 4",
        "escalation_handler":  "Person 5",
        "clarification_handler": "Person 1",
    }
    trace = []
    for name in agents_called:
        clean_name = name.replace("(ERROR)", "").strip()
        entry = next((a for a in audit_trail if a.get("agent") == clean_name), {})
        trace.append({
            "agent": clean_name.replace("_", " ").title(),
            "owner": owner_map.get(clean_name, "Team"),
            "output": {"action": entry.get("action", ""),
                       "details": entry.get("details", "")[:80]},
        })
    return trace


def run_real_pipeline(
    query: str,
    order_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Invoke the team's LangGraph pipeline and translate its output into the
    shape the existing UI components already expect.

    This is the one true integration entry point. The UI itself doesn't change.
    """
    if not _REAL_BACKEND_AVAILABLE:
        raise RuntimeError(
            f"Real backend not available. Import error: {_BACKEND_IMPORT_ERROR}"
        )

    import time as _time
    start = _time.time()

    # If caller didn't pass an explicit order_id, try to extract one from the
    # message text. Their backend trusts whatever order_id we pass and won't
    # parse the message itself — so we extract here to keep parity with the
    # mock pipeline behavior.
    if not order_id:
        m = ORDER_ID_REGEX.search(query)
        if m:
            order_id = m.group(1).upper()

    initial_state = {
        "session_id":           f"ui-{int(start)}",
        "customer_id":          customer_id or "CUST_1001",
        "channel":              "web",
        "message":              query,
        "conversation_history": [],
    }
    if order_id:
        initial_state["order_id"] = order_id

    final = _real_graph_app.invoke(initial_state)
    elapsed_ms = int((_time.time() - start) * 1000)

    intent_out = {
        "intent":            _intent_title(final.get("intent", "unknown")),
        "confidence":        float(final.get("intent_confidence", 0.0)),
        "sentiment":         _sentiment_title(final.get("sentiment", "neutral")),
        "urgency":           _urgency_title(final.get("urgency", "low")),
        "keywords_matched":  [],
    }

    order_ctx = _adapt_order_context(
        final.get("order_context"),
        customer_id or final.get("customer_id", ""),
    )

    policy_out = _adapt_policy(final.get("policy_snippets"))
    workflow_out = _adapt_workflow(
        final.get("action_taken"),
        final.get("action_result"),
        final.get("escalation_required", False),
    )
    risk_out = _adapt_risk(
        float(final.get("risk_score", 0.0)),
        bool(final.get("escalation_required", False)),
        final.get("escalation_reason", ""),
        final.get("target_team", ""),
    )

    product_out = final.get("product_context") or None
    if product_out and "comparison" in product_out:
        comp = product_out.get("comparison") or []
        if len(comp) >= 2 and product_out.get("mode") == "comparison":
            products = []
            for p in comp[:2]:
                specs = p.get("specs") or {}
                products.append({
                    "name":          p.get("name", ""),
                    "brand":         p.get("name", "").split()[0] if p.get("name") else "",
                    "processor":     specs.get("processor", "N/A"),
                    "price_inr":     p.get("price", 0),
                    "ram_gb":        int(str(specs.get("ram", "0")).replace("GB", "") or 0),
                    "storage_gb":    int(str(specs.get("storage", "0")).replace("GB", "") or 0),
                    "battery_hours": int(str(specs.get("battery", "0")).replace("h", "") or 0),
                    "rating":        p.get("rating", 0),
                    "in_stock":      p.get("in_stock", True),
                    "best_for":      p.get("best_for", ""),
                })
            rec_text = product_out.get("recommendation", "")
            winner_name = rec_text.split(" — ")[0].strip() if " — " in rec_text else products[0]["name"]
            product_out = {
                "mode":           "comparison",
                "products":       products,
                "scores":         product_out.get("scores", {}),
                "recommendation": winner_name,
                "reason":         rec_text.split(" — ", 1)[1] if " — " in rec_text else rec_text,
                "alternatives":   product_out.get("alternatives", []),
            }

    quality = float(final.get("quality_score", 0.0))
    eval_out = {
        "score":   int(quality * 100),
        "verdict": _verdict_from_quality(quality),
        "notes":   final.get("quality_issues") or ["No issues flagged"],
    }

    trace = _adapt_trace(
        final.get("agents_called") or [],
        final.get("audit_trail") or [],
    )

    return {
        "query":         query,
        "intent":        intent_out,
        "order_context": order_ctx,
        "policy":        policy_out,
        "product":       product_out,
        "workflow":      workflow_out,
        "risk":          risk_out,
        "response":      final.get("response_text", "No response generated."),
        "evaluation":    eval_out,
        "latency_ms":    elapsed_ms,
        "trace":         trace,
    }
