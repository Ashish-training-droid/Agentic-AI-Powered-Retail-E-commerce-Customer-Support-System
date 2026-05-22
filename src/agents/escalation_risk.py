"""
Escalation & Risk Agent (Rohan (Person 5))

Detects high-risk, low-confidence, angry, fraud, or compliance-sensitive
cases and routes them to the correct human team. Replaces the original
stub with a multi-factor weighted risk matrix, two-band decision logic
(auto / approval_required / escalate), explainable factor breakdowns,
and SLA-aware routing.

Responsibilities
----------------
- Read schema-typed state produced by upstream agents (Ashish (Person 1), 2, 3).
- Score risk on six independent factors with documented weights.
- Decide one of three outcomes:
    * ``auto``               : safe for the AI to answer end-to-end.
    * ``approval_required``  : draft response, human must approve (HITL).
    * ``escalate``           : hand off entirely to the routed human team.
- Pick the highest-severity matching escalation route (not the last-matched).
- Emit a per-factor breakdown so the agent console / audit log can show
  *why* the system decided what it did.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import CONFIDENCE_THRESHOLD_LOW
from src.orchestrator.state import AgentState

# ---------------------------------------------------------------------------
# Tunable thresholds
# ---------------------------------------------------------------------------
# Two bands give us precision/recall control:
#   risk_score < FLAG_THRESHOLD            -> auto answer
#   FLAG_THRESHOLD <= score < ESCALATE     -> human approves AI draft (HITL)
#   risk_score >= ESCALATE_THRESHOLD       -> direct escalation, no AI response
FLAG_THRESHOLD: float = 0.40
ESCALATE_THRESHOLD: float = 0.70
# Matched routes at or above this severity force "escalate" even on a low
# score — for P1 emergencies the right answer is "skip the AI entirely".
FORCE_ESCALATE_SEVERITY: int = 80
# Matched routes BELOW this severity do not, on their own, push the case
# into HITL. They still appear in `matched_routes` for explainability and
# still contribute to the weighted risk_score, but a single low-severity
# signal (e.g. policy_exception=30 because the KB had no snippet, or
# low_confidence=40 from a vague message) is no longer enough to demand
# human approval — that was making the agent trigger-happy on routine
# order-tracking and FAQ traffic. Real risk signals (repeated_contact=50
# and above) still flag.
MIN_FLAG_ROUTE_SEVERITY: int = 50

# Order-value bands (INR). Tuned for the ShopEase catalog distribution.
HIGH_VALUE_THRESHOLD: int = 10_000
MODERATE_VALUE_THRESHOLD: int = 5_000

# Repeated-contact thresholds (number of CRM notes on file).
# Tuned to "only flag at 4 or above". The MODERATE band is set above HIGH on
# purpose so it never fires — customers with 0-3 notes contribute nothing to
# risk, only 4+ contribute the full weight. This avoids dragging chatty regular
# customers into HITL on routine order-tracking traffic.
REPEATED_CONTACT_HIGH: int = 4
REPEATED_CONTACT_MODERATE: int = 5

# Fraud signal: refunds inside the rolling window count toward suspicion.
FRAUD_REFUND_COUNT_HIGH: int = 3
FRAUD_REFUND_COUNT_MODERATE: int = 2

# ---------------------------------------------------------------------------
# Factor weights (must sum to 1.0)
# ---------------------------------------------------------------------------
WEIGHTS: dict[str, float] = {
    "sentiment": 0.25,
    "order_value": 0.20,
    "intent_confidence": 0.15,
    "customer_tier": 0.10,
    "repeated_contact": 0.15,
    "issue_severity": 0.15,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Risk factor weights must sum to 1.0"

# ---------------------------------------------------------------------------
# Raw factor lookup tables
# ---------------------------------------------------------------------------
SENTIMENT_SCORE: dict[str, float] = {
    "positive": 0.0,
    "neutral": 0.1,
    "negative": 0.4,
    "angry": 0.8,
}

CUSTOMER_TIER_SCORE: dict[str, float] = {
    "regular": 0.0,
    "premium": 0.3,
    "vip": 0.6,
}

# Issue severity by intent (1.0 = critical, 0.0 = routine).
INTENT_SEVERITY: dict[str, float] = {
    "damaged_product": 1.0,
    "delivery_complaint": 0.7,
    "refund_status": 0.5,
    "return_request": 0.4,
    "warranty": 0.4,
    "coupon_issue": 0.2,
    "order_tracking": 0.1,
    "product_inquiry": 0.0,
    "general_faq": 0.0,
}

# ---------------------------------------------------------------------------
# Escalation routes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EscalationRoute:
    """A single escalation destination with team, priority, and SLA."""

    code: str
    team: str
    priority: str          # P1 (most urgent) ... P4 (least)
    sla_hours: int
    severity: int          # Higher wins when multiple routes match.
    description: str


ESCALATION_ROUTES: dict[str, EscalationRoute] = {
    "fraud": EscalationRoute(
        code="fraud",
        team="fraud_review",
        priority="P1",
        sla_hours=1,
        severity=100,
        description="Fraud signals detected (duplicate refunds / chargeback / disputed payment)",
    ),
    "angry_high_value": EscalationRoute(
        code="angry_high_value",
        team="senior_agent",
        priority="P1",
        sla_hours=2,
        severity=90,
        description="Angry customer with a high-value order",
    ),
    "damaged_high_value": EscalationRoute(
        code="damaged_high_value",
        team="replacement_team",
        priority="P2",
        sla_hours=4,
        severity=80,
        description="Damaged high-value product requires specialist review",
    ),
    "payment_dispute": EscalationRoute(
        code="payment_dispute",
        team="refund_specialist",
        priority="P2",
        sla_hours=4,
        severity=75,
        description="Payment / chargeback dispute requires refund specialist",
    ),
    "lost_shipment": EscalationRoute(
        code="lost_shipment",
        team="logistics",
        priority="P2",
        sla_hours=4,
        severity=70,
        description="Shipment marked as lost — needs logistics + fraud review",
    ),
    "vip_attention": EscalationRoute(
        code="vip_attention",
        team="senior_agent",
        priority="P2",
        sla_hours=2,
        severity=60,
        description="VIP customer with a non-trivial issue — preserve white-glove SLA",
    ),
    "repeated_contact": EscalationRoute(
        code="repeated_contact",
        team="escalation_queue",
        priority="P3",
        sla_hours=8,
        severity=50,
        description="Customer has contacted multiple times on the same issue",
    ),
    "low_confidence": EscalationRoute(
        code="low_confidence",
        team="senior_agent",
        priority="P3",
        sla_hours=8,
        severity=40,
        description="Low classification confidence — needs human review",
    ),
    "policy_exception": EscalationRoute(
        code="policy_exception",
        team="manager",
        priority="P3",
        sla_hours=12,
        severity=30,
        description="No matching policy retrieved for a policy-dependent intent",
    ),
}


# ---------------------------------------------------------------------------
# Risk factor model
# ---------------------------------------------------------------------------
@dataclass
class RiskFactor:
    """One contributor to the overall risk score."""

    name: str
    raw: float        # 0.0-1.0 unweighted signal strength
    weight: float     # Factor weight (sums to 1.0 across factors)
    detail: str       # Human-readable explanation (shown in agent console)

    @property
    def contribution(self) -> float:
        return round(self.raw * self.weight, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "raw": round(self.raw, 4),
            "weight": self.weight,
            "contribution": self.contribution,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_get(d: Any, *keys: str, default: Any = None) -> Any:
    """Nested dict getter that never raises on missing keys / non-dict types."""
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _order_value(state: AgentState) -> int:
    val = _safe_get(state, "order_context", "payment", "amount", default=0)
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def _payment_status(state: AgentState) -> str:
    return str(_safe_get(state, "order_context", "payment", "status", default="") or "").lower()


def _shipment_status(state: AgentState) -> str:
    return str(_safe_get(state, "order_context", "shipment", "status", default="") or "").lower()


def _customer_tier(state: AgentState) -> str:
    tier = state.get("customer_tier") or _safe_get(state, "order_context", "customer_tier", default="regular")
    return str(tier or "regular").lower()


def _crm_note_count(state: AgentState) -> int:
    notes = _safe_get(state, "order_context", "crm_notes", default=[])
    return len(notes) if isinstance(notes, list) else 0


def _return_history_count(state: AgentState) -> int:
    history = _safe_get(state, "order_context", "return_history", default=[])
    return len(history) if isinstance(history, list) else 0


# ---------------------------------------------------------------------------
# Factor computations
# ---------------------------------------------------------------------------
def _factor_sentiment(state: AgentState) -> RiskFactor:
    sentiment = str(state.get("sentiment") or "neutral").lower()
    raw = SENTIMENT_SCORE.get(sentiment, 0.1)
    return RiskFactor(
        name="sentiment",
        raw=raw,
        weight=WEIGHTS["sentiment"],
        detail=f"sentiment={sentiment}",
    )


def _factor_order_value(state: AgentState) -> RiskFactor:
    amount = _order_value(state)
    if amount >= HIGH_VALUE_THRESHOLD:
        raw, label = 0.8, "high"
    elif amount >= MODERATE_VALUE_THRESHOLD:
        raw, label = 0.5, "moderate"
    elif amount > 0:
        raw, label = 0.1, "low"
    else:
        raw, label = 0.0, "unknown"
    return RiskFactor(
        name="order_value",
        raw=raw,
        weight=WEIGHTS["order_value"],
        detail=f"amount={amount} ({label})",
    )


def _factor_intent_confidence(state: AgentState) -> RiskFactor:
    confidence = float(state.get("intent_confidence") or 0.0)
    if confidence < CONFIDENCE_THRESHOLD_LOW:
        raw, label = 1.0, "very low"
    elif confidence < 0.7:
        raw, label = 0.5, "moderate"
    else:
        raw, label = 0.0, "high"
    return RiskFactor(
        name="intent_confidence",
        raw=raw,
        weight=WEIGHTS["intent_confidence"],
        detail=f"confidence={confidence:.2f} ({label})",
    )


def _factor_customer_tier(state: AgentState) -> RiskFactor:
    tier = _customer_tier(state)
    raw = CUSTOMER_TIER_SCORE.get(tier, 0.0)
    return RiskFactor(
        name="customer_tier",
        raw=raw,
        weight=WEIGHTS["customer_tier"],
        detail=f"tier={tier}",
    )


def _factor_repeated_contact(state: AgentState) -> RiskFactor:
    note_count = _crm_note_count(state)
    if note_count >= REPEATED_CONTACT_HIGH:
        raw, label = 1.0, "high"
    elif note_count >= REPEATED_CONTACT_MODERATE:
        raw, label = 0.5, "moderate"
    else:
        raw, label = 0.0, "none"
    return RiskFactor(
        name="repeated_contact",
        raw=raw,
        weight=WEIGHTS["repeated_contact"],
        detail=f"crm_notes={note_count} ({label})",
    )


def _factor_issue_severity(state: AgentState) -> RiskFactor:
    intent = str(state.get("intent") or "").lower()
    raw = INTENT_SEVERITY.get(intent, 0.1)
    return RiskFactor(
        name="issue_severity",
        raw=raw,
        weight=WEIGHTS["issue_severity"],
        detail=f"intent={intent or 'unknown'}",
    )


def calculate_risk_factors(state: AgentState) -> list[RiskFactor]:
    """Return the six weighted factors for a given state."""
    return [
        _factor_sentiment(state),
        _factor_order_value(state),
        _factor_intent_confidence(state),
        _factor_customer_tier(state),
        _factor_repeated_contact(state),
        _factor_issue_severity(state),
    ]


def calculate_risk_score(state: AgentState) -> float:
    """Composite 0.0-1.0 risk score across all factors."""
    score = sum(f.contribution for f in calculate_risk_factors(state))
    return round(min(max(score, 0.0), 1.0), 4)


# ---------------------------------------------------------------------------
# Route matching (deterministic, severity-ordered)
# ---------------------------------------------------------------------------
def _matched_routes(state: AgentState) -> list[EscalationRoute]:
    """Evaluate every routing rule and return matches sorted by severity desc."""
    intent = str(state.get("intent") or "").lower()
    sentiment = str(state.get("sentiment") or "neutral").lower()
    confidence = float(state.get("intent_confidence") or 1.0)
    tier = _customer_tier(state)
    order_value = _order_value(state)
    payment_status = _payment_status(state)
    shipment_status = _shipment_status(state)
    crm_notes = _crm_note_count(state)
    refund_count = _return_history_count(state)
    policy_snippets = state.get("policy_snippets") or []
    policy_required_intents = {"return_request", "refund_status", "warranty", "coupon_issue", "damaged_product"}

    matches: list[EscalationRoute] = []

    # Fraud / payment integrity signals
    if refund_count >= FRAUD_REFUND_COUNT_HIGH:
        matches.append(ESCALATION_ROUTES["fraud"])
    if payment_status in {"disputed", "chargeback"}:
        matches.append(ESCALATION_ROUTES["payment_dispute"])

    # Sentiment + value combo (the original P1 case)
    if sentiment == "angry" and order_value >= MODERATE_VALUE_THRESHOLD:
        matches.append(ESCALATION_ROUTES["angry_high_value"])

    # Product/shipment-specific
    if intent == "damaged_product" and order_value >= HIGH_VALUE_THRESHOLD:
        matches.append(ESCALATION_ROUTES["damaged_high_value"])
    if shipment_status == "lost":
        matches.append(ESCALATION_ROUTES["lost_shipment"])

    # VIP retention SLA — keep white glove even for moderate issues
    if tier == "vip" and intent in {"return_request", "refund_status", "damaged_product", "delivery_complaint"}:
        matches.append(ESCALATION_ROUTES["vip_attention"])

    # Behavioral signals
    if crm_notes >= REPEATED_CONTACT_HIGH:
        matches.append(ESCALATION_ROUTES["repeated_contact"])

    # System confidence signals
    if confidence < CONFIDENCE_THRESHOLD_LOW:
        matches.append(ESCALATION_ROUTES["low_confidence"])
    if intent in policy_required_intents and not policy_snippets:
        matches.append(ESCALATION_ROUTES["policy_exception"])

    return sorted(matches, key=lambda r: r.severity, reverse=True)


# ---------------------------------------------------------------------------
# Banded decision logic (auto / approval_required / escalate)
# ---------------------------------------------------------------------------
def _decide_band(score: float, top_route: EscalationRoute | None) -> str:
    """Map score + top matched route to a band.

    Precedence:
        1. ``top_route.severity >= FORCE_ESCALATE_SEVERITY`` -> escalate
           (P1 emergencies always skip the AI).
        2. ``score >= ESCALATE_THRESHOLD``                   -> escalate.
        3. ``score >= FLAG_THRESHOLD`` OR matched route at or above
           ``MIN_FLAG_ROUTE_SEVERITY`` (50)                  -> approval_required.
           Low-severity routes (policy_exception=30,
           low_confidence=40) no longer auto-flag on their own; they
           still contribute to the weighted risk_score and remain in
           ``matched_routes`` for explainability.
        4. Otherwise                                         -> auto.
    """
    if top_route is not None and top_route.severity >= FORCE_ESCALATE_SEVERITY:
        return "escalate"
    if score >= ESCALATE_THRESHOLD:
        return "escalate"
    if score >= FLAG_THRESHOLD:
        return "approval_required"
    if top_route is not None and top_route.severity >= MIN_FLAG_ROUTE_SEVERITY:
        return "approval_required"
    return "auto"


def _sla_target_iso(route: EscalationRoute | None) -> str:
    if route is None:
        return ""
    target = datetime.now(timezone.utc) + timedelta(hours=route.sla_hours)
    return target.isoformat()


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------
def check_risk(state: AgentState) -> AgentState:
    """
    LangGraph node: evaluates risk and decides auto / HITL / escalate.

    Reads:
        intent, sentiment, urgency, intent_confidence, customer_tier,
        order_context (payment.amount, payment.status, shipment.status,
        crm_notes, return_history), policy_snippets

    Writes:
        risk_score, risk_band, risk_factors, escalation_required,
        escalation_reason, target_team, priority, sla_target,
        requires_human_approval, agents_called, audit_trail
    """
    factors = calculate_risk_factors(state)
    score = round(sum(f.contribution for f in factors), 4)
    score = round(min(max(score, 0.0), 1.0), 4)

    routes = _matched_routes(state)
    top_route = routes[0] if routes else None
    band = _decide_band(score, top_route=top_route)

    if band == "escalate" and top_route is None:
        # Score was high enough to escalate but no rule fired — route to a
        # senior agent so a human can interpret the borderline signal.
        top_route = ESCALATION_ROUTES["low_confidence"]

    escalation_required = band == "escalate"
    requires_human_approval = band == "approval_required"

    if top_route is not None and band != "auto":
        target_team = top_route.team
        priority = top_route.priority
        escalation_reason = top_route.description
        sla_target = _sla_target_iso(top_route)
    else:
        target_team = ""
        priority = "P4"
        escalation_reason = ""
        sla_target = ""

    update: dict[str, Any] = {
        "risk_score": score,
        "risk_band": band,
        "risk_factors": [f.to_dict() for f in factors],
        "matched_routes": [asdict(r) for r in routes],
        "escalation_required": escalation_required,
        "escalation_reason": escalation_reason,
        "target_team": target_team,
        "priority": priority,
        "sla_target": sla_target,
        "requires_human_approval": requires_human_approval,
        "agents_called": ["escalation_risk"],
        "audit_trail": [{
            "agent": "escalation_risk",
            "action": "evaluate_risk",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": (
                f"score={score:.2f} band={band} "
                f"route={top_route.code if top_route else 'none'} "
                f"team={target_team or 'n/a'} priority={priority} "
                f"approval={requires_human_approval}"
            ),
        }],
    }
    return update
