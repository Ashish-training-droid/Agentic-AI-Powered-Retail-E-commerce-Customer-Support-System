"""
Metrics and performance tracking utilities.

Tracks agent latency, resolution rates, quality scores, and
generates summary reports for evaluation.
"""

from __future__ import annotations
import time
import functools
from datetime import datetime, timezone
from typing import Callable, Any
from dataclasses import dataclass, field


@dataclass
class AgentMetrics:
    """Container for per-agent performance metrics."""
    agent_name: str
    calls: int = 0
    total_latency_ms: float = 0.0
    errors: int = 0
    escalations: int = 0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.calls if self.calls > 0 else 0.0

    @property
    def error_rate(self) -> float:
        return self.errors / self.calls if self.calls > 0 else 0.0


@dataclass
class SessionMetrics:
    """Container for per-session (conversation) metrics."""
    session_id: str
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: str = ""
    agents_called: list[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    intent: str = ""
    resolved: bool = False
    escalated: bool = False
    quality_score: float = 0.0
    response_confidence: float = 0.0


# Global metrics store (in production, replace with proper metrics backend)
_agent_metrics: dict[str, AgentMetrics] = {}
_session_metrics: list[SessionMetrics] = []


def track_latency(func: Callable) -> Callable:
    """
    Decorator to track execution time of agent functions.

    Usage:
        @track_latency
        def classify_intent(state):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            agent_name = func.__name__
            if agent_name not in _agent_metrics:
                _agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)

            _agent_metrics[agent_name].calls += 1
            _agent_metrics[agent_name].total_latency_ms += elapsed_ms

            return result
        except Exception as e:
            agent_name = func.__name__
            if agent_name not in _agent_metrics:
                _agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)
            _agent_metrics[agent_name].errors += 1
            raise
    return wrapper


def compute_resolution_metrics(results: list[dict]) -> dict:
    """
    Compute aggregate metrics from a batch of conversation results.

    Args:
        results: List of final AgentState dicts from completed conversations

    Returns:
        Dictionary with summary metrics
    """
    if not results:
        return {"total": 0}

    total = len(results)
    escalated = sum(1 for r in results if r.get("escalation_required", False))
    resolved = total - escalated

    confidences = [r.get("response_confidence", 0) for r in results]
    quality_scores = [r.get("quality_score", 0) for r in results]

    intent_distribution: dict[str, int] = {}
    for r in results:
        intent = r.get("intent", "unknown")
        intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

    return {
        "total_conversations": total,
        "resolved_by_ai": resolved,
        "escalated_to_human": escalated,
        "resolution_rate": resolved / total,
        "escalation_rate": escalated / total,
        "avg_response_confidence": sum(confidences) / total,
        "avg_quality_score": sum(quality_scores) / total,
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
        "intent_distribution": intent_distribution,
    }


def get_agent_metrics() -> dict[str, dict]:
    """Return current agent performance metrics."""
    return {
        name: {
            "calls": m.calls,
            "avg_latency_ms": round(m.avg_latency_ms, 2),
            "error_rate": round(m.error_rate, 4),
            "errors": m.errors,
        }
        for name, m in _agent_metrics.items()
    }


def reset_metrics():
    """Reset all metrics (useful between test runs)."""
    global _agent_metrics, _session_metrics
    _agent_metrics = {}
    _session_metrics = []
