"""
product_advisory.py
===================

Person 4's signature agent. Compares two products side-by-side, picks a
winner with a transparent score, and suggests alternatives when an item
is out of stock.

PUBLIC FUNCTIONS:
  advise_products(query, product_a, product_b, use_case) -> dict
  list_categories()                                       -> list[str]
  list_products_by_category(category)                     -> list[str]
  get_product(name)                                       -> dict
  build_comparison_table(product_a, product_b)            -> pandas.DataFrame
  find_alternatives(product_name)                         -> list[dict]

WHY THIS LIVES IN ITS OWN MODULE:
The other agents are mocks that will be replaced by teammates.
Product Advisory is the agent Person 4 actually owns end-to-end,
so it gets its own file with all the comparison logic.
"""

from __future__ import annotations

import pandas as pd

from .mock_agents import load_products


# Fields shown in the side-by-side comparison table. Each tuple is
# (column_name_in_csv, label_shown_to_user).
SPEC_FIELDS = [
    ("name",             "Model"),
    ("brand",            "Brand"),
    ("processor",        "Processor"),
    ("price_inr",        "Price (₹)"),
    ("ram_gb",           "RAM (GB)"),
    ("storage_gb",       "Storage (GB)"),
    ("battery_hours",    "Battery (hrs)"),
    ("display_inch",     "Display (in)"),
    ("weight_kg",        "Weight (kg)"),
    ("warranty_months",  "Warranty (months)"),
    ("rating",           "Rating"),
    ("in_stock",         "In Stock"),
    ("best_for",         "Best For"),
    ("key_features",     "Key Features"),
]


# -----------------------------------------------------------------------------
# Catalog helpers (used by the UI dropdowns)
# -----------------------------------------------------------------------------

def list_categories() -> list[str]:
    """Return all distinct product categories in the catalog, sorted."""
    df = load_products()
    return sorted(df["category"].unique().tolist())


def list_products_by_category(category: str) -> list[str]:
    """Return all product names in a given category."""
    df = load_products()
    return df[df["category"] == category]["name"].tolist()


def get_product(name: str) -> dict:
    """Return one product row as a dict (or {} if not found)."""
    df = load_products()
    row = df[df["name"] == name]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


# -----------------------------------------------------------------------------
# Comparison
# -----------------------------------------------------------------------------

def build_comparison_table(product_a: str, product_b: str) -> pd.DataFrame:
    """Return a tidy DataFrame: one row per spec, two columns (A and B).
    This is what the UI renders as the side-by-side comparison table.
    """
    a = get_product(product_a)
    b = get_product(product_b)
    rows = []
    for csv_key, label in SPEC_FIELDS:
        rows.append({
            "Specification": label,
            product_a: str(a.get(csv_key)),
            product_b: str(b.get(csv_key)),
        })
    return pd.DataFrame(rows)


def _score(product: dict, use_case: str | None) -> float:
    """Compute a single numeric score for one product.

    Higher is better. The formula is intentionally simple so we can
    explain it on the demo slide:
        score = rating * 10
              + battery_hours * 0.5
              + ram_gb * 0.8
              - price / 5000           (cheaper is better)
              + 5  if in stock
              + 8  if matches use case
    """
    s = 0.0
    s += product["rating"] * 10
    s += (product["battery_hours"] or 0) * 0.5
    s += (product["ram_gb"] or 0) * 0.8
    s -= product["price_inr"] / 5000
    if product["in_stock"]:
        s += 5
    if use_case and use_case.lower() in str(product["best_for"]).lower():
        s += 8
    return round(s, 2)


def _explain_winner(winner: dict, loser: dict) -> str:
    """Build a human-readable 'why' string for the recommendation."""
    bits: list[str] = []
    if winner["rating"] > loser["rating"]:
        bits.append(f"higher customer rating ({winner['rating']}★ vs {loser['rating']}★)")
    if (winner["battery_hours"] or 0) > (loser["battery_hours"] or 0):
        bits.append(f"longer battery ({winner['battery_hours']}h vs {loser['battery_hours']}h)")
    if (winner["ram_gb"] or 0) > (loser["ram_gb"] or 0):
        bits.append(f"more RAM ({winner['ram_gb']}GB vs {loser['ram_gb']}GB)")
    if winner["in_stock"] and not loser["in_stock"]:
        bits.append("currently in stock while the other is unavailable")
    if not bits:
        bits.append("balanced specs but stronger overall fit for the stated use case")
    return "Recommended because of " + ", ".join(bits) + "."


def _compare_two(a: dict, b: dict, use_case: str | None) -> dict:
    """Run the full two-product comparison and pick a winner."""
    sa, sb = _score(a, use_case), _score(b, use_case)
    winner = a if sa >= sb else b
    loser  = b if winner is a else a

    df = load_products()
    return {
        "mode":           "comparison",
        "products":       [a, b],
        "scores":         {a["name"]: sa, b["name"]: sb},
        "recommendation": winner["name"],
        "reason":         _explain_winner(winner, loser),
        "alternatives":   _suggest_alternatives(winner, df, exclude_top=True),
    }


def _suggest_alternatives(top: dict, df: pd.DataFrame, exclude_top: bool = True) -> list[dict]:
    """Return up to 3 in-stock alternatives in the same category, top-rated first."""
    cat_df = df[(df["category"] == top["category"]) & (df["in_stock"])]
    if exclude_top:
        cat_df = cat_df[cat_df["product_id"] != top["product_id"]]
    cat_df = cat_df.sort_values(by="rating", ascending=False).head(3)
    return cat_df[["product_id", "name", "brand", "price_inr", "rating", "in_stock"]].to_dict(orient="records")


# -----------------------------------------------------------------------------
# Free-text extraction (so the chat tab can do "Compare X vs Y")
# -----------------------------------------------------------------------------

def _extract_product_names(query: str) -> tuple[str | None, str | None]:
    """Pull up to two product names out of a free-text customer message.

    Greedy longest-match against the catalog. Used by the chat tab so the
    Product Advisory Agent can be triggered without explicit form inputs.
    """
    df = load_products()
    msg_lower = query.lower()
    # Sort longest names first so e.g. "IdeaBook Slim 5" wins over "Slim".
    names = sorted(df["name"].tolist(), key=len, reverse=True)
    found: list[str] = []
    for n in names:
        if n.lower() in msg_lower and n not in found:
            found.append(n)
            if len(found) == 2:
                break
    return (found[0] if len(found) > 0 else None,
            found[1] if len(found) > 1 else None)


def _category_from_query(query: str) -> str | None:
    """Detect category from a free-text query (e.g. 'best laptop for college')."""
    q = query.lower()
    if "laptop" in q or "macbook" in q or "notebook" in q:
        return "Laptop"
    if "phone" in q or "mobile" in q or "iphone" in q:
        return "Phone"
    if "headphone" in q or "earphone" in q or "earbud" in q:
        return "Headphones"
    return None


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

def advise_products(
    query: str = "",
    product_a: str | None = None,
    product_b: str | None = None,
    use_case: str | None = None,
) -> dict:
    """The Product Advisory Agent.

    Three modes — picked automatically:
      • "comparison"     when two products are named (via args or in `query`)
      • "recommendation" when only a category is known (e.g. "best laptop")
      • "none"           when nothing can be extracted

    Returns: {mode, products, recommendation, reason, alternatives, ...}
    """
    df = load_products()

    # If only `query` was passed, try to pull product names and use case out of it.
    if not (product_a and product_b) and query:
        a_guess, b_guess = _extract_product_names(query)
        product_a = product_a or a_guess
        product_b = product_b or b_guess

    if not use_case and query:
        for hint in ["college", "gaming", "photography", "travel", "office", "students"]:
            if hint in query.lower():
                use_case = hint.capitalize()
                break

    # MODE 1: explicit comparison between two named products ------------------
    if product_a and product_b:
        a = df[df["name"] == product_a].iloc[0].to_dict()
        b = df[df["name"] == product_b].iloc[0].to_dict()
        return _compare_two(a, b, use_case)

    # MODE 2: recommend from a category ---------------------------------------
    cat = _category_from_query(query)
    if cat:
        cat_df = df[df["category"] == cat].copy()
        if use_case:
            filtered = cat_df[cat_df["best_for"].str.contains(use_case, case=False, na=False)]
            if not filtered.empty:
                cat_df = filtered
        cat_df = cat_df.sort_values(by=["in_stock", "rating"], ascending=[False, False])
        top = cat_df.iloc[0].to_dict()
        return {
            "mode":           "recommendation",
            "products":       [top],
            "recommendation": top["name"],
            "reason":         f"Top-rated {cat.lower()} ({top['rating']}★) currently in stock, "
                              f"well-suited for {top['best_for']}.",
            "alternatives":   _suggest_alternatives(top, df, exclude_top=True),
        }

    # MODE 3: nothing to advise on --------------------------------------------
    return {
        "mode": "none",
        "products": [],
        "recommendation": None,
        "reason": "Could not identify a product category in the query.",
        "alternatives": [],
    }


# Convenience aliases — used by app.py for the dedicated comparison tab.

def compare(product_a: str, product_b: str, use_case: str | None = None) -> dict:
    """Force the comparison mode (UI shortcut)."""
    return advise_products(query="", product_a=product_a, product_b=product_b, use_case=use_case)


def find_alternatives(product_name: str) -> list[dict]:
    """If a product is out of stock, return in-stock alternatives.
    Returns an empty list if the product is already in stock.
    """
    df = load_products()
    row = df[df["name"] == product_name]
    if row.empty:
        return []
    top = row.iloc[0].to_dict()
    if top["in_stock"]:
        return []
    alts = df[(df["category"] == top["category"]) & (df["in_stock"])].copy()
    alts = alts.sort_values(by="rating", ascending=False).head(3)
    return alts[["product_id", "name", "brand", "price_inr", "rating", "best_for"]].to_dict(orient="records")
