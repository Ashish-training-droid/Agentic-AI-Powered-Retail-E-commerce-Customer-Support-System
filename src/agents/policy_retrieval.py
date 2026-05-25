"""
Policy Retrieval Agent (Gunjan (Person 2))

Searches approved return, refund, warranty, delivery, seller, coupon, and
general policies. Loads policies from JSON files in src/knowledge/policies/
and matches them via intent + keyword scoring.

Returns matched policy snippets with reference IDs and confidence scores.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from src.orchestrator.state import AgentState


# --------------------------------------------------------------------------
# Knowledge base loading
# --------------------------------------------------------------------------

POLICY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "knowledge",
    "policies",
)

POLICY_FILES = [
    "return_policy.json",
    "refund_policy.json",
    "warranty_policy.json",
    "delivery_policy.json",
    "coupon_policy.json",
    "seller_policy.json",
    "general_faq.json",
]

# Maps intents (from intent_classifier) to policy categories/subcategories.
INTENT_TO_CATEGORIES = {
    "return_request":      ["return"],
    "refund_status":       ["refund"],
    "warranty":            ["warranty"],
    "coupon_issue":        ["coupon"],
    "delivery_complaint":  ["delivery"],
    "damaged_product":     ["damaged_product", "return"],
    "order_tracking":      ["delivery"],
    "general_faq":         ["general", "cancellation"],
    "product_inquiry":     [],
}


@lru_cache(maxsize=1)
def _load_all_policies() -> tuple:
    """Load every rule from every policy JSON file. Cached after first call."""
    all_rules: list[dict[str, Any]] = []
    for filename in POLICY_FILES:
        path = os.path.join(POLICY_DIR, filename)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            all_rules.extend(data.get("rules", []))
        except (json.JSONDecodeError, OSError):
            continue
    # Return as tuple so it's hashable for lru_cache
    return tuple(all_rules)


# --------------------------------------------------------------------------
# Matching / scoring
# --------------------------------------------------------------------------

def _score_rule(rule: dict[str, Any], intent: str, message: str) -> float:
    """
    Score a single policy rule against the customer intent + message.
    Returns a confidence value between 0.0 and 1.0.
    """
    score = 0.0
    msg_lower = (message or "").lower()
    rule_category = rule.get("category", "")
    target_categories = INTENT_TO_CATEGORIES.get(intent, [])

    # 1) Strong signal: rule's category matches the intent's expected categories
    if rule_category in target_categories:
        score += 0.6

    # 2) Keyword overlap with the customer message
    keywords = [k.lower() for k in rule.get("keywords", [])]
    if keywords and msg_lower:
        hits = sum(1 for kw in keywords if kw in msg_lower)
        if hits:
            score += min(0.35, 0.12 * hits)

    # 3) Subcategory keyword in message (small boost)
    subcat = rule.get("subcategory", "").lower()
    if subcat and subcat.replace("_", " ") in msg_lower:
        score += 0.05

    return round(min(score, 0.99), 2)


def _build_snippet(rule: dict[str, Any], confidence: float) -> dict[str, Any]:
    """Convert a raw policy rule into the PolicySnippet shape the state expects."""
    explanation_bits = []
    if rule.get("conditions"):
        explanation_bits.append("Conditions: " + "; ".join(rule["conditions"][:3]))
    if rule.get("exceptions"):
        explanation_bits.append("Exceptions: " + "; ".join(rule["exceptions"][:2]))

    return {
        "rule": rule.get("rule", ""),
        "explanation": " | ".join(explanation_bits) if explanation_bits else rule.get("subcategory", ""),
        "reference_id": rule.get("policy_id", "POL-UNKNOWN"),
        "confidence": confidence,
    }


# --------------------------------------------------------------------------
# Public agent function — DO NOT change the signature
# --------------------------------------------------------------------------

def _retrieve_with_embeddings(intent: str, message: str) -> list[dict]:
    """Use vector embeddings for semantic policy search (LIVE mode)."""
    try:
        from src.knowledge.embedding_store import get_embedding_store
        store = get_embedding_store()
        return store.search(query=message, intent=intent, top_k=3, min_score=0.3)
    except Exception:
        return []


def _retrieve_with_keywords(intent: str, message: str) -> list[dict]:
    """Use keyword matching for policy search (MOCK mode / fallback)."""
    rules = _load_all_policies()
    scored: list[tuple[float, dict[str, Any]]] = []
    for rule in rules:
        conf = _score_rule(rule, intent, message)
        if conf >= 0.5:
            scored.append((conf, rule))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]
    return [_build_snippet(rule, conf) for conf, rule in top]


def retrieve_policy(state: AgentState) -> AgentState:
    """
    LangGraph node: retrieves relevant policy snippets for the detected intent.

    Uses vector embeddings (OpenAI) in LIVE mode for semantic search.
    Falls back to keyword matching in MOCK mode or if embeddings fail.

    Reads:  intent, message, order_context
    Writes: policy_snippets, policy_applies, agents_called, audit_trail
    """
    from src.config import USE_MOCK, OPENAI_API_KEY

    intent = state.get("intent", "") or ""
    message = state.get("message", "") or ""
    retrieval_method = "keywords"

    if not USE_MOCK and OPENAI_API_KEY:
        snippets = _retrieve_with_embeddings(intent, message)
        if snippets:
            retrieval_method = "embeddings"
        else:
            snippets = _retrieve_with_keywords(intent, message)
    else:
        snippets = _retrieve_with_keywords(intent, message)

    policy_applies = len(snippets) > 0

    return {
        "policy_snippets": snippets,
        "policy_applies": policy_applies,
        "agents_called": ["policy_retrieval"],
        "audit_trail": [{
            "agent": "policy_retrieval",
            "action": "retrieve_policy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": (
                f"method={retrieval_method}, intent={intent}, "
                f"matches_found={len(snippets)}, applies={policy_applies}"
            ),
        }],
    }