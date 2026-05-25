"""
Product Advisory Agent (Aditi (Person 4))

Compares products, checks compatibility, suggests alternatives, and provides
availability information from the product catalog.

This implementation is the real one (replacing the original stub). It is a
direct port of shopease_capstone/modules/product_advisory.py, wrapped as a
LangGraph node so it integrates with Person 1's orchestrator.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator.state import AgentState


# -----------------------------------------------------------------------------
# Catalog loading (JSON from src/knowledge/products/)
# -----------------------------------------------------------------------------

_CATALOG_PATH = (
    Path(__file__).parent.parent
    / "knowledge"
    / "products"
    / "catalog.json"
)


def _load_catalog() -> list[dict]:
    """Load the product catalog from JSON. Returns a list of product dicts."""
    if not _CATALOG_PATH.exists():
        return []
    import json as _json
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        data = _json.load(f)
    products = data.get("products", []) if isinstance(data, dict) else data
    return products


# -----------------------------------------------------------------------------
# Free-text parsing
# -----------------------------------------------------------------------------

def _extract_product_names(query: str, catalog: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """Find up to two known product names mentioned in the customer message."""
    msg = query.lower()
    names = sorted([r["name"] for r in catalog], key=len, reverse=True)
    found: list[str] = []
    for n in names:
        if n.lower() in msg and n not in found:
            found.append(n)
            if len(found) == 2:
                break
    return (found[0] if found else None,
            found[1] if len(found) > 1 else None)


def _category_from_query(query: str) -> Optional[str]:
    q = query.lower()
    if "laptop" in q or "macbook" in q or "notebook" in q:
        return "Laptop"
    if "phone" in q or "mobile" in q or "iphone" in q:
        return "Phone"
    if "headphone" in q or "earphone" in q or "earbud" in q:
        return "Headphones"
    return None


def _use_case_from_query(query: str) -> Optional[str]:
    for hint in ["college", "gaming", "photography", "travel", "office", "students"]:
        if hint in query.lower():
            return hint.capitalize()
    return None


# -----------------------------------------------------------------------------
# Scoring + comparison
# -----------------------------------------------------------------------------

def _score(product: dict, use_case: Optional[str]) -> float:
    s = 0.0
    s += product.get("rating", 0) * 10
    s += (product.get("battery_hours") or 0) * 0.5
    s += (product.get("ram_gb") or 0) * 0.8
    s -= (product.get("price_inr") or 0) / 5000
    if product.get("in_stock"):
        s += 5
    if use_case and use_case.lower() in str(product.get("best_for", "")).lower():
        s += 8
    return round(s, 2)


def _explain_winner(winner: dict, loser: dict) -> str:
    bits: list[str] = []
    if winner.get("rating", 0) > loser.get("rating", 0):
        bits.append(f"higher customer rating ({winner['rating']}★ vs {loser['rating']}★)")
    if (winner.get("battery_hours") or 0) > (loser.get("battery_hours") or 0):
        bits.append(f"longer battery ({winner['battery_hours']}h vs {loser['battery_hours']}h)")
    if (winner.get("ram_gb") or 0) > (loser.get("ram_gb") or 0):
        bits.append(f"more RAM ({winner['ram_gb']}GB vs {loser['ram_gb']}GB)")
    if winner.get("in_stock") and not loser.get("in_stock"):
        bits.append("currently in stock while the other is unavailable")
    if not bits:
        bits.append("balanced specs but stronger overall fit for the stated use case")
    return "Recommended because of " + ", ".join(bits) + "."


def _suggest_alternatives(top: dict, catalog: list[dict]) -> list[dict]:
    same_cat = [r for r in catalog
                if r.get("category") == top.get("category")
                and r.get("in_stock")
                and r.get("product_id") != top.get("product_id")]
    same_cat.sort(key=lambda r: r.get("rating", 0), reverse=True)
    return [{"name": r["name"], "brand": r["brand"],
             "price_inr": r["price_inr"], "rating": r["rating"]}
            for r in same_cat[:3]]


def _compare_two(a: dict, b: dict, use_case: Optional[str], catalog: list[dict]) -> dict:
    sa, sb = _score(a, use_case), _score(b, use_case)
    winner = a if sa >= sb else b
    loser = b if winner is a else a

    return {
        "mode": "comparison",
        "comparison": [
            {"name": a["name"], "price": a["price_inr"],
             "specs": {"ram": f"{a['ram_gb']}GB", "storage": f"{a['storage_gb']}GB",
                       "processor": a.get("processor", "N/A"),
                       "battery": f"{a['battery_hours']}h"},
             "rating": a["rating"], "best_for": a.get("best_for", ""),
             "in_stock": a["in_stock"]},
            {"name": b["name"], "price": b["price_inr"],
             "specs": {"ram": f"{b['ram_gb']}GB", "storage": f"{b['storage_gb']}GB",
                       "processor": b.get("processor", "N/A"),
                       "battery": f"{b['battery_hours']}h"},
             "rating": b["rating"], "best_for": b.get("best_for", ""),
             "in_stock": b["in_stock"]},
        ],
        "recommendation": f"{winner['name']} — {_explain_winner(winner, loser)}",
        "scores": {a["name"]: sa, b["name"]: sb},
        "alternatives": _suggest_alternatives(winner, catalog),
    }


# -----------------------------------------------------------------------------
# LangGraph node entry point
# -----------------------------------------------------------------------------

def advise_product(state: AgentState) -> AgentState:
    """LangGraph node: product comparison + recommendations.

    Reads: message
    Writes: product_context, agents_called, audit_trail
    """
    message = state.get("message", "")
    catalog = _load_catalog()
    products_found = 0

    if not catalog:
        product_context = {
            "comparison": [],
            "recommendation": ("Product catalog unavailable. Please ensure "
                               "shopease_capstone/data/products.csv exists."),
        }
    else:
        a_name, b_name = _extract_product_names(message, catalog)
        use_case = _use_case_from_query(message)

        # MODE 1: two products named -> head-to-head comparison
        if a_name and b_name:
            a = next(r for r in catalog if r["name"] == a_name)
            b = next(r for r in catalog if r["name"] == b_name)
            product_context = _compare_two(a, b, use_case, catalog)
            products_found = 2

        # MODE 2: a category is mentioned -> recommend the top product
        else:
            cat = _category_from_query(message)
            if cat:
                in_cat = [r for r in catalog if r.get("category") == cat]
                if use_case:
                    filtered = [r for r in in_cat
                                if use_case.lower() in str(r.get("best_for", "")).lower()]
                    if filtered:
                        in_cat = filtered
                in_cat.sort(key=lambda r: (not r.get("in_stock"), -r.get("rating", 0)))
                if in_cat:
                    top = in_cat[0]
                    product_context = {
                        "mode": "recommendation",
                        "comparison": [{
                            "name": top["name"], "price": top["price_inr"],
                            "specs": {"ram": f"{top['ram_gb']}GB",
                                      "storage": f"{top['storage_gb']}GB",
                                      "processor": top.get("processor", "N/A"),
                                      "battery": f"{top['battery_hours']}h"},
                            "rating": top["rating"],
                            "best_for": top.get("best_for", ""),
                            "in_stock": top["in_stock"],
                        }],
                        "recommendation": (
                            f"{top['name']} — top-rated {cat.lower()} "
                            f"({top['rating']}★), well-suited for {top.get('best_for', '')}."
                        ),
                        "alternatives": _suggest_alternatives(top, catalog),
                    }
                    products_found = 1
                else:
                    product_context = {
                        "comparison": [],
                        "recommendation": f"No {cat.lower()}s currently available in the catalog.",
                    }
            else:
                product_context = {
                    "comparison": [],
                    "recommendation": ("I can help you compare products. Could you tell me "
                                       "which category (laptop, phone, headphones) or specific "
                                       "products you're interested in?"),
                }

    return {
        "product_context": product_context,
        "agents_called": ["product_advisory"],
        "audit_trail": [{
            "agent": "product_advisory",
            "action": "product_search",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"products_found={products_found}",
        }],
    }
