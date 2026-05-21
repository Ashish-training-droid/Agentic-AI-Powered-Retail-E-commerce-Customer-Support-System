"""
Human-in-the-Loop Approval Queue (Person 5)

For risk_band == "approval_required" cases, the AI drafts a response but
must not deliver it until a human approves. This module stores the draft
in a JSONL queue and exposes a tiny CLI for reviewers.

Storage layout
--------------
- ``logs/approvals.jsonl`` : append-only journal of every state change
                             (submit, approve, reject). Latest line wins
                             per ``approval_id``.

Why JSONL and not SQLite?
-------------------------
- Zero dependencies, atomic line appends, easy to diff in git, easy to
  inspect in a demo. The volume for this prototype is tiny.

Demo aid
--------
Setting ``APPROVAL_AUTO_APPROVE=true`` (env var) makes ``submit_for_approval``
auto-approve immediately so the live demo doesn't stall waiting for a human.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_QUEUE_PATH = Path("logs") / "approvals.jsonl"

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_AUTO_APPROVED = "auto_approved"


@dataclass
class ApprovalRecord:
    """One state-change entry. The queue is reconstructed by replaying these."""

    approval_id: str
    session_id: str
    customer_id: str
    submitted_at: str
    status: str
    intent: str
    risk_score: float
    target_team: str
    priority: str
    sla_target: str
    draft_response: str
    references_cited: list[str] = field(default_factory=list)
    risk_factors: list[dict[str, Any]] = field(default_factory=list)
    reviewer: str = ""
    decided_at: str = ""
    decision_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _resolve_path(filepath: str | os.PathLike[str] | None) -> Path:
    path = Path(filepath) if filepath else DEFAULT_QUEUE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _append(record: ApprovalRecord, filepath: str | os.PathLike[str] | None = None) -> Path:
    path = _resolve_path(filepath)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record.to_dict(), ensure_ascii=False, default=str) + "\n")
    return path


def _replay(filepath: str | os.PathLike[str] | None = None) -> dict[str, ApprovalRecord]:
    """Read the JSONL and collapse to the latest record per approval_id."""
    path = _resolve_path(filepath)
    if not path.exists():
        return {}
    latest: dict[str, ApprovalRecord] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                rec = ApprovalRecord(**data)
                latest[rec.approval_id] = rec
            except (json.JSONDecodeError, TypeError):
                continue
    return latest


# ---------------------------------------------------------------------------
# Public API used by the graph
# ---------------------------------------------------------------------------
def submit_for_approval(
    *,
    session_id: str,
    customer_id: str,
    intent: str,
    risk_score: float,
    target_team: str,
    priority: str,
    sla_target: str,
    draft_response: str,
    references_cited: list[str] | None = None,
    risk_factors: list[dict[str, Any]] | None = None,
    filepath: str | os.PathLike[str] | None = None,
) -> ApprovalRecord:
    """Submit a drafted response for human approval.

    Returns the ``ApprovalRecord`` (id, status). Auto-approves if the
    ``APPROVAL_AUTO_APPROVE=true`` env var is set (demo convenience).
    """
    auto = os.getenv("APPROVAL_AUTO_APPROVE", "false").lower() == "true"
    status = STATUS_AUTO_APPROVED if auto else STATUS_PENDING

    record = ApprovalRecord(
        approval_id=f"APR-{uuid.uuid4().hex[:8].upper()}",
        session_id=session_id,
        customer_id=customer_id,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        intent=intent,
        risk_score=risk_score,
        target_team=target_team,
        priority=priority,
        sla_target=sla_target,
        draft_response=draft_response,
        references_cited=list(references_cited or []),
        risk_factors=list(risk_factors or []),
        reviewer="auto" if auto else "",
        decided_at=datetime.now(timezone.utc).isoformat() if auto else "",
        decision_note="auto-approved (APPROVAL_AUTO_APPROVE=true)" if auto else "",
    )
    _append(record, filepath)
    return record


def list_pending(filepath: str | os.PathLike[str] | None = None) -> list[ApprovalRecord]:
    return [r for r in _replay(filepath).values() if r.status == STATUS_PENDING]


def get(approval_id: str, filepath: str | os.PathLike[str] | None = None) -> ApprovalRecord | None:
    return _replay(filepath).get(approval_id)


def _decide(
    approval_id: str,
    *,
    status: str,
    reviewer: str,
    note: str,
    filepath: str | os.PathLike[str] | None,
) -> ApprovalRecord | None:
    current = get(approval_id, filepath)
    if current is None:
        return None
    if current.status not in (STATUS_PENDING,):
        # Already decided; return as-is so callers can detect idempotently.
        return current
    updated = ApprovalRecord(
        **{**current.to_dict(), "status": status,
           "reviewer": reviewer,
           "decided_at": datetime.now(timezone.utc).isoformat(),
           "decision_note": note}
    )
    _append(updated, filepath)
    return updated


def approve(
    approval_id: str,
    *,
    reviewer: str = "",
    note: str = "",
    filepath: str | os.PathLike[str] | None = None,
) -> ApprovalRecord | None:
    return _decide(approval_id, status=STATUS_APPROVED, reviewer=reviewer, note=note, filepath=filepath)


def reject(
    approval_id: str,
    *,
    reviewer: str = "",
    note: str = "",
    filepath: str | os.PathLike[str] | None = None,
) -> ApprovalRecord | None:
    return _decide(approval_id, status=STATUS_REJECTED, reviewer=reviewer, note=note, filepath=filepath)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_record(rec: ApprovalRecord, *, full: bool = False) -> None:
    line = (
        f"{rec.approval_id}  {rec.status:<14}  {rec.priority}  "
        f"{rec.intent:<20}  risk={rec.risk_score:.2f}  team={rec.target_team or '-'}"
    )
    print(line)
    if full:
        print(f"  session   : {rec.session_id}")
        print(f"  customer  : {rec.customer_id}")
        print(f"  submitted : {rec.submitted_at}")
        print(f"  sla       : {rec.sla_target or '-'}")
        print(f"  reviewer  : {rec.reviewer or '-'}")
        print(f"  decided   : {rec.decided_at or '-'}")
        if rec.references_cited:
            print(f"  refs      : {', '.join(rec.references_cited)}")
        print(f"  draft     : {rec.draft_response}")
        if rec.decision_note:
            print(f"  note      : {rec.decision_note}")


def _cmd_list(args: argparse.Namespace) -> int:
    records = _replay(args.file).values()
    if args.status:
        records = [r for r in records if r.status == args.status]
    records = sorted(records, key=lambda r: r.submitted_at)
    if not records:
        print("(no records)")
        return 0
    for rec in records:
        _print_record(rec, full=args.verbose)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    rec = get(args.approval_id, args.file)
    if rec is None:
        print(f"No approval record found for {args.approval_id}", file=sys.stderr)
        return 1
    _print_record(rec, full=True)
    return 0


def _cmd_approve(args: argparse.Namespace) -> int:
    rec = approve(args.approval_id, reviewer=args.reviewer, note=args.note or "", filepath=args.file)
    if rec is None:
        print(f"No approval record found for {args.approval_id}", file=sys.stderr)
        return 1
    _print_record(rec, full=True)
    return 0


def _cmd_reject(args: argparse.Namespace) -> int:
    rec = reject(args.approval_id, reviewer=args.reviewer, note=args.note or "", filepath=args.file)
    if rec is None:
        print(f"No approval record found for {args.approval_id}", file=sys.stderr)
        return 1
    _print_record(rec, full=True)
    return 0


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.governance.approval_queue",
        description="Review human-in-the-loop approval requests from the escalation agent.",
    )
    parser.add_argument("--file", default=None, help="Path to approvals.jsonl (default: logs/approvals.jsonl)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List approval records (default: all)")
    p_list.add_argument("--status", choices=[STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_AUTO_APPROVED])
    p_list.add_argument("--verbose", "-v", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="Show one approval record in full")
    p_show.add_argument("approval_id")
    p_show.set_defaults(func=_cmd_show)

    p_approve = sub.add_parser("approve", help="Approve a pending request")
    p_approve.add_argument("approval_id")
    p_approve.add_argument("--reviewer", default=os.getenv("USER") or os.getenv("USERNAME") or "human")
    p_approve.add_argument("--note", default="")
    p_approve.set_defaults(func=_cmd_approve)

    p_reject = sub.add_parser("reject", help="Reject a pending request")
    p_reject.add_argument("approval_id")
    p_reject.add_argument("--reviewer", default=os.getenv("USER") or os.getenv("USERNAME") or "human")
    p_reject.add_argument("--note", default="")
    p_reject.set_defaults(func=_cmd_reject)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_cli()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
