"""
Audit Log (Person 5)

Append-only audit trail for every conversation that flows through the
orchestration graph. Stored as JSONL so it's easy to grep, easy to load
into pandas, and survives crashes (atomic line appends).

Used by:
    * The graph's terminal nodes (write one entry per resolved session).
    * ``tests/evaluation/run_evaluation.py`` (read entries to compute
      escalation precision / recall, false-escalation rate, latency).
    * The agent console (Person 4) for the "raw audit log" panel.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.orchestrator.state import AgentState

DEFAULT_AUDIT_PATH = Path("logs") / "audit.jsonl"


@dataclass
class AuditEntry:
    """One row of the audit log. Designed to be append-only."""

    session_id: str
    timestamp: str
    customer_id: str
    channel: str
    message: str
    intent_detected: str
    intent_confidence: float
    sentiment: str
    urgency: str
    agents_called: list[str] = field(default_factory=list)
    policy_references: list[str] = field(default_factory=list)
    action_taken: str = ""
    action_success: bool | None = None
    risk_score: float = 0.0
    risk_band: str = "auto"                # "auto" | "approval_required" | "escalate"
    risk_factors: list[dict[str, Any]] = field(default_factory=list)
    escalation: bool = False
    escalation_reason: str = ""
    target_team: str = ""
    priority: str = "P4"
    sla_target: str = ""
    approval_status: str = "n/a"           # "auto" | "pending" | "approved" | "rejected" | "n/a"
    approval_id: str = ""
    response_confidence: float = 0.0
    quality_score: float = 0.0
    quality_issues: list[str] = field(default_factory=list)
    human_override: bool = False
    resolution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _action_success(state: AgentState) -> bool | None:
    action_result = state.get("action_result")
    if not isinstance(action_result, dict):
        return None
    if "success" in action_result:
        return bool(action_result["success"])
    return None


def _derive_approval_status(state: AgentState) -> str:
    """Default approval_status from risk_band if it wasn't set explicitly."""
    explicit = state.get("approval_status")
    if explicit:
        return str(explicit)
    band = str(state.get("risk_band") or "").lower()
    if band == "approval_required":
        return "pending"
    if band == "escalate":
        return "n/a"
    return "auto"


def build_audit_entry_from_state(state: AgentState, *, resolution_time_ms: float = 0.0) -> AuditEntry:
    """Map a finished ``AgentState`` into an ``AuditEntry``.

    Pulled out so the same code path is used in production (graph terminals)
    and in tests (evaluation harness) — same numbers, same shape.
    """
    return AuditEntry(
        session_id=str(state.get("session_id") or ""),
        timestamp=datetime.now(timezone.utc).isoformat(),
        customer_id=str(state.get("customer_id") or ""),
        channel=str(state.get("channel") or "web"),
        message=str(state.get("message") or ""),
        intent_detected=str(state.get("intent") or ""),
        intent_confidence=float(state.get("intent_confidence") or 0.0),
        sentiment=str(state.get("sentiment") or "neutral"),
        urgency=str(state.get("urgency") or "medium"),
        agents_called=list(state.get("agents_called") or []),
        policy_references=list(state.get("references_cited") or []),
        action_taken=str(state.get("action_taken") or ""),
        action_success=_action_success(state),
        risk_score=float(state.get("risk_score") or 0.0),
        risk_band=str(state.get("risk_band") or "auto"),
        risk_factors=list(state.get("risk_factors") or []),
        escalation=bool(state.get("escalation_required") or False),
        escalation_reason=str(state.get("escalation_reason") or ""),
        target_team=str(state.get("target_team") or ""),
        priority=str(state.get("priority") or "P4"),
        sla_target=str(state.get("sla_target") or ""),
        approval_status=_derive_approval_status(state),
        approval_id=str(state.get("approval_id") or ""),
        response_confidence=float(state.get("response_confidence") or 0.0),
        quality_score=float(state.get("quality_score") or 0.0),
        quality_issues=list(state.get("quality_issues") or []),
        human_override=bool(state.get("human_override") or False),
        resolution_time_ms=float(resolution_time_ms),
    )


# ---------------------------------------------------------------------------
# Persistence (atomic line append; safe to call from anywhere)
# ---------------------------------------------------------------------------
def _resolve_path(filepath: str | os.PathLike[str] | None) -> Path:
    path = Path(filepath) if filepath else DEFAULT_AUDIT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_audit_log(entry: AuditEntry, filepath: str | os.PathLike[str] | None = None) -> Path:
    """Append a single entry to the JSONL audit log."""
    path = _resolve_path(filepath)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.to_dict(), ensure_ascii=False, default=str) + "\n")
    return path


def load_audit_logs(filepath: str | os.PathLike[str] | None = None) -> list[AuditEntry]:
    """Load all entries. Skips malformed lines rather than crashing."""
    path = _resolve_path(filepath)
    if not path.exists():
        return []
    entries: list[AuditEntry] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(AuditEntry(**data))
            except (json.JSONDecodeError, TypeError):
                continue
    return entries


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _avg(values: Iterable[float]) -> float:
    values = list(values)
    return round(sum(values) / len(values), 4) if values else 0.0


def generate_audit_report(logs: list[AuditEntry] | None = None) -> dict[str, Any]:
    """Aggregate metrics across audit entries.

    Pass ``logs=None`` to load from the default file. Returns a dict that's
    safe to ``json.dumps()`` and to render in the agent console.
    """
    if logs is None:
        logs = load_audit_logs()

    total = len(logs)
    if total == 0:
        return {
            "total_sessions": 0,
            "note": "no audit entries on disk yet",
        }

    escalations = [e for e in logs if e.escalation]
    approvals = [e for e in logs if e.risk_band == "approval_required"]
    auto = [e for e in logs if e.risk_band == "auto"]

    return {
        "total_sessions": total,
        "escalation_rate": round(len(escalations) / total, 4),
        "approval_required_rate": round(len(approvals) / total, 4),
        "auto_resolution_rate": round(len(auto) / total, 4),
        "human_override_rate": round(sum(1 for e in logs if e.human_override) / total, 4),
        "avg_risk_score": _avg(e.risk_score for e in logs),
        "avg_response_confidence": _avg(e.response_confidence for e in logs),
        "avg_quality_score": _avg(e.quality_score for e in logs),
        "avg_resolution_time_ms": _avg(e.resolution_time_ms for e in logs),
        "intent_distribution": dict(Counter(e.intent_detected for e in logs).most_common()),
        "sentiment_distribution": dict(Counter(e.sentiment for e in logs).most_common()),
        "team_distribution": dict(
            Counter(e.target_team for e in escalations if e.target_team).most_common()
        ),
        "priority_distribution": dict(
            Counter(e.priority for e in escalations).most_common()
        ),
    }
