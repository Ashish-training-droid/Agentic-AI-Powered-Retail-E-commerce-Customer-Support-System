"""
Vector Embedding Store for Policy RAG

Uses OpenAI embeddings to create a simple vector store for policy retrieval.
Embeds all policy rules at startup, then finds the most relevant policies
for any customer query using cosine similarity.

This replaces keyword matching with semantic search — "I want my money back"
will match "Refunds are processed within 5-7 days" even with no shared keywords.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from functools import lru_cache

from langchain_openai import OpenAIEmbeddings
from src.config import OPENAI_API_KEY


POLICY_DIR = Path(__file__).parent / "policies"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class PolicyEmbeddingStore:
    """Simple vector store for policy documents using OpenAI embeddings."""

    def __init__(self):
        self.embeddings_model = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model="text-embedding-3-small",
        )
        self.policies: list[dict] = []
        self.policy_embeddings: list[list[float]] = []
        self._loaded = False

    def load_policies(self):
        """Load all policy files and embed them."""
        if self._loaded:
            return

        all_rules = []
        for policy_file in POLICY_DIR.glob("*.json"):
            try:
                with open(policy_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rules = data.get("rules", [])
                all_rules.extend(rules)
            except (json.JSONDecodeError, OSError):
                continue

        if not all_rules:
            self._loaded = True
            return

        self.policies = all_rules

        # Create text for embedding: combine rule + conditions + keywords
        texts = []
        for rule in all_rules:
            text_parts = [
                rule.get("rule", ""),
                " ".join(rule.get("conditions", [])),
                " ".join(rule.get("keywords", [])),
                rule.get("subcategory", ""),
            ]
            texts.append(" ".join(text_parts))

        # Embed all policies in one batch
        self.policy_embeddings = self.embeddings_model.embed_documents(texts)
        self._loaded = True

    def search(self, query: str, intent: str = "", top_k: int = 3, min_score: float = 0.3) -> list[dict]:
        """
        Find the most relevant policies for a customer query.

        Args:
            query: Customer message
            intent: Detected intent (used to boost relevant categories)
            top_k: Number of results to return
            min_score: Minimum similarity score to include

        Returns:
            List of policy snippets with confidence scores
        """
        if not self._loaded:
            self.load_policies()

        if not self.policies or not self.policy_embeddings:
            return []

        # Embed the query
        query_text = f"{intent} {query}" if intent else query
        query_embedding = self.embeddings_model.embed_query(query_text)

        # Calculate similarity with all policies
        scores = []
        for i, policy_emb in enumerate(self.policy_embeddings):
            similarity = _cosine_similarity(query_embedding, policy_emb)
            scores.append((similarity, i))

        # Sort by similarity (highest first)
        scores.sort(key=lambda x: x[0], reverse=True)

        # Return top_k results above min_score
        results = []
        for score, idx in scores[:top_k]:
            if score < min_score:
                break
            rule = self.policies[idx]
            results.append({
                "rule": rule.get("rule", ""),
                "explanation": "; ".join(rule.get("conditions", [])[:2]),
                "reference_id": rule.get("policy_id", "POL-UNKNOWN"),
                "confidence": round(min(score * 1.2, 0.99), 2),
            })

        return results


# Singleton instance
_store: PolicyEmbeddingStore | None = None


def get_embedding_store() -> PolicyEmbeddingStore:
    """Get or create the singleton embedding store."""
    global _store
    if _store is None:
        _store = PolicyEmbeddingStore()
    return _store
