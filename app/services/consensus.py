"""
PHASE 14 — Consensus Engine (ELITE hard gate).

A match must pass BOTH of these or it is dropped entirely — it never
reaches the ranking engine, never gets persisted, never shows up in any tier:

    1. NO-3 score >= 85   (low blowout risk)
    2. Safety score >= 85 (at most one minor deduction allowed)

Requiring Safety == 100 is too strict in practice: any match with
dominance > 50 takes a -15 deduction, leaving 85 — perfectly acceptable
risk — but would have been silently dropped under the old rule.  >= 85
lets those matches through while still blocking truly dangerous fixtures
(dominance > 50 AND early-goal risk >= 61 would land at 65, still rejected).

Matches that clear this gate are labeled tier "ELITE".
Dominance/odds/form are still computed upstream and stored on the
prediction for context, but they no longer gate inclusion — NO-3 and
Safety are the only two hard requirements.
"""
from app.services.scoring_types import MatchContext

NO3_PASS_THRESHOLD = 85.0
SAFETY_PASS_THRESHOLD = 85.0  # relaxed from 100 — see docstring above


def evaluate_consensus(ctx: MatchContext) -> tuple[bool, int]:
    no3_ok = ctx.no3_score >= NO3_PASS_THRESHOLD
    safety_ok = ctx.safety_score >= SAFETY_PASS_THRESHOLD

    passed = no3_ok and safety_ok
    votes = int(no3_ok) + int(safety_ok)  # kept for display ("2/2" style badges)

    ctx.passed_consensus = passed
    ctx.consensus_votes = votes

    if not passed:
        reasons = []
        if not no3_ok:
            reasons.append(f"NO-3 {ctx.no3_score:.1f} < {NO3_PASS_THRESHOLD:.0f}")
        if not safety_ok:
            reasons.append(f"Safety {ctx.safety_score:.1f} < {SAFETY_PASS_THRESHOLD:.0f}")
        ctx.reject("; ".join(reasons))

    return passed, votes
