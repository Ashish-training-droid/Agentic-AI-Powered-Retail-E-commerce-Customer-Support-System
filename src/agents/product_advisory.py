"""
Product Advisory Agent (Person 4)

Compares products, checks compatibility, suggests alternatives, and provides
availability information from the product catalog.

TODO(Person 4): Replace mock data with actual product catalog search.
Build comparison logic using product specs, price bands, ratings, and
customer needs analysis.
"""

from __future__ import annotations
from datetime import datetime, timezone

from src.orchestrator.state import AgentState


# Mock product catalog — Person 4 will replace with full catalog + search
MOCK_PRODUCTS = {
    "laptop": {
        "comparison": [
            {
                "name": "HP Pavilion 15",
                "price": 55999,
                "specs": {"ram": "16GB", "storage": "512GB SSD", "processor": "Intel i5-13th Gen", "display": "15.6 inch FHD"},
                "rating": 4.3,
                "best_for": "college students, everyday use",
                "in_stock": True,
            },
            {
                "name": "Lenovo IdeaPad Slim 5",
                "price": 52999,
                "specs": {"ram": "16GB", "storage": "512GB SSD", "processor": "AMD Ryzen 5 7530U", "display": "15.6 inch FHD"},
                "rating": 4.4,
                "best_for": "budget-conscious students, light gaming",
                "in_stock": True,
            },
            {
                "name": "ASUS VivoBook 15",
                "price": 48999,
                "specs": {"ram": "8GB", "storage": "512GB SSD", "processor": "Intel i5-12th Gen", "display": "15.6 inch FHD"},
                "rating": 4.1,
                "best_for": "basic college work, browsing",
                "in_stock": False,
                "alternative": "ASUS VivoBook 14 (in stock, Rs 45999)",
            },
        ],
        "recommendation": "For college use, we recommend the Lenovo IdeaPad Slim 5 for best value or HP Pavilion 15 for better build quality.",
    },
    "headphones": {
        "comparison": [
            {
                "name": "Sony WH-1000XM5",
                "price": 24999,
                "specs": {"type": "Over-ear", "anc": "Yes", "battery": "30 hours", "connectivity": "Bluetooth 5.2"},
                "rating": 4.7,
                "best_for": "premium noise cancellation, travel",
                "in_stock": True,
            },
            {
                "name": "JBL Tune 770NC",
                "price": 4999,
                "specs": {"type": "Over-ear", "anc": "Yes", "battery": "44 hours", "connectivity": "Bluetooth 5.3"},
                "rating": 4.2,
                "best_for": "budget ANC, long battery life",
                "in_stock": True,
            },
        ],
        "recommendation": "For best audio quality, Sony WH-1000XM5. For budget-friendly ANC, JBL Tune 770NC.",
    },
}


def advise_product(state: AgentState) -> AgentState:
    """
    LangGraph node: provides product comparison and recommendations.

    Reads: message, intent
    Writes: product_context, agents_called, audit_trail

    TODO(Person 4): Replace with:
      1. Parse product names/categories from message
      2. Search product catalog with filters
      3. Compare specs side-by-side
      4. Check inventory availability
      5. Suggest alternatives for out-of-stock items
    """
    message = state.get("message", "").lower()

    product_context = {}
    for keyword, data in MOCK_PRODUCTS.items():
        if keyword in message:
            product_context = data
            break

    if not product_context:
        product_context = {
            "comparison": [],
            "recommendation": "I can help you compare products. Could you tell me what category or specific products you're interested in?",
        }

    return {
        "product_context": product_context,
        "agents_called": ["product_advisory"],
        "audit_trail": [{
            "agent": "product_advisory",
            "action": "product_search",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"products_found={len(product_context.get('comparison', []))}",
        }],
    }
