"""Governance layer owned by Person 5.

Modules:
    audit            : append-only audit log + report generation
    approval_queue   : human-in-the-loop approval queue (JSONL + CLI)
"""

from src.governance.audit import (
    AuditEntry,
    build_audit_entry_from_state,
    generate_audit_report,
    load_audit_logs,
    save_audit_log,
)
from src.governance.approval_queue import (
    ApprovalRecord,
    approve,
    list_pending,
    reject,
    submit_for_approval,
)

__all__ = [
    "AuditEntry",
    "ApprovalRecord",
    "approve",
    "build_audit_entry_from_state",
    "generate_audit_report",
    "list_pending",
    "load_audit_logs",
    "reject",
    "save_audit_log",
    "submit_for_approval",
]
