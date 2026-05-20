"""
ShopEase Agentic AI Support System — Demo Runner

Runs sample customer conversations through the full LangGraph pipeline,
showing each step: intent classification -> routing -> context gathering ->
evaluation -> risk check -> response generation.

Usage:
    python -m src.main              # Run all demos
    python -m src.main --demo 1     # Run specific demo (1-7)
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

from src.orchestrator.graph import app


def load_sample_conversations() -> list[dict]:
    """Load demo conversations from JSON file."""
    data_path = Path(__file__).parent.parent / "data" / "mock" / "sample_conversations.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_header(text: str, char: str = "="):
    """Print formatted section header."""
    width = 70
    print(f"\n{char * width}")
    print(f"  {text}")
    print(f"{char * width}")


def print_step(step_name: str, details: dict):
    """Print a pipeline step with its output."""
    print(f"\n  [{step_name}]")
    for key, value in details.items():
        if isinstance(value, dict):
            print(f"    {key}:")
            for k, v in value.items():
                print(f"      {k}: {v}")
        elif isinstance(value, list) and value:
            print(f"    {key}:")
            for item in value[:3]:
                if isinstance(item, dict):
                    print(f"      - {item}")
                else:
                    print(f"      - {item}")
        else:
            print(f"    {key}: {value}")


def run_demo(conversation: dict):
    """Run a single conversation through the pipeline and display results."""
    print_header(f"DEMO: {conversation['description']}")

    print(f"\n  Customer ({conversation['channel']}): \"{conversation['message']}\"")
    print(f"  Customer ID: {conversation['customer_id']}")
    print(f"  Expected Intent: {conversation['expected_intent']}")
    print(f"  Expected Outcome: {conversation['expected_outcome']}")

    # Prepare initial state
    initial_state = {
        "session_id": f"session_{conversation['id']}",
        "customer_id": conversation["customer_id"],
        "channel": conversation["channel"],
        "message": conversation["message"],
        "conversation_history": [],
    }

    print("\n  --- Pipeline Execution ---")

    # Run the graph
    result = app.invoke(initial_state)

    # Display results step by step
    print_step("Intent Classification", {
        "intent": result.get("intent", "?"),
        "sentiment": result.get("sentiment", "?"),
        "urgency": result.get("urgency", "?"),
        "confidence": result.get("intent_confidence", 0),
    })

    if result.get("order_context"):
        print_step("Order Context", {
            "order_id": result["order_context"].get("order_id", "N/A"),
            "status": result["order_context"].get("status", "N/A"),
            "customer_tier": result.get("customer_tier", "N/A"),
        })

    if result.get("policy_snippets"):
        print_step("Policy Retrieval", {
            "policies_found": len(result["policy_snippets"]),
            "top_policy": result["policy_snippets"][0].get("rule", "")[:80] + "..." if result["policy_snippets"] else "None",
            "reference": result["policy_snippets"][0].get("reference_id", "") if result["policy_snippets"] else "N/A",
        })

    if result.get("product_context") and result["product_context"].get("comparison"):
        print_step("Product Advisory", {
            "products_compared": len(result["product_context"]["comparison"]),
            "recommendation": result["product_context"].get("recommendation", "")[:80],
        })

    if result.get("action_taken"):
        print_step("Workflow Action", {
            "action": result.get("action_taken", "none"),
            "success": result.get("action_result", {}).get("success", False),
            "details": result.get("action_result", {}).get("message", ""),
        })

    print_step("Quality Evaluation", {
        "quality_score": f"{result.get('quality_score', 0):.2f}",
        "issues": result.get("quality_issues", []) or "None",
    })

    print_step("Risk Assessment", {
        "risk_score": f"{result.get('risk_score', 0):.2f}",
        "escalation_required": result.get("escalation_required", False),
        "target_team": result.get("target_team", "N/A") or "N/A",
        "priority": result.get("priority", "P4"),
    })

    # Final response
    print_header("FINAL RESPONSE", "-")
    print(f"\n  {result.get('response_text', 'No response generated.')}")
    print(f"\n  Confidence: {result.get('response_confidence', 0):.2f}")
    if result.get("references_cited"):
        print(f"  References: {', '.join(result['references_cited'])}")
    if result.get("suggested_next_action"):
        print(f"  Next Action: {result['suggested_next_action']}")

    # Audit trail summary
    agents_called = result.get("agents_called", [])
    print(f"\n  Agents Called: {' -> '.join(agents_called)}")
    print(f"{'=' * 70}")

    return result


def main():
    """Main entry point for the demo runner."""
    conversations = load_sample_conversations()

    # Check if a specific demo was requested
    if len(sys.argv) > 2 and sys.argv[1] == "--demo":
        try:
            demo_idx = int(sys.argv[2]) - 1
            if 0 <= demo_idx < len(conversations):
                conversations = [conversations[demo_idx]]
            else:
                print(f"Demo number must be between 1 and {len(conversations)}")
                sys.exit(1)
        except ValueError:
            print("Usage: python -m src.main [--demo N]")
            sys.exit(1)

    print_header("ShopEase Agentic AI Support System — Demo", "*")
    print(f"\n  Running {len(conversations)} demo conversation(s)")
    print(f"  Mode: {'MOCK (no API calls)' if not __import__('src.config', fromlist=['OPENAI_API_KEY']).OPENAI_API_KEY else 'LIVE (OpenAI)'}")

    results = []
    for conv in conversations:
        result = run_demo(conv)
        results.append(result)

    # Summary
    print_header("EXECUTION SUMMARY", "*")
    print(f"\n  Total conversations: {len(results)}")
    escalated = sum(1 for r in results if r.get("escalation_required"))
    print(f"  Escalated: {escalated}")
    print(f"  Resolved by AI: {len(results) - escalated}")
    avg_confidence = sum(r.get("response_confidence", 0) for r in results) / len(results) if results else 0
    print(f"  Average response confidence: {avg_confidence:.2f}")
    avg_quality = sum(r.get("quality_score", 0) for r in results) / len(results) if results else 0
    print(f"  Average quality score: {avg_quality:.2f}")
    print()


if __name__ == "__main__":
    main()
