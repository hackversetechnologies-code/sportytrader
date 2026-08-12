"""
PHASE 14 — Consensus Engine (ELITE hard gate).

Updated rule: this is no longer a "4 of 5 votes" system. A match must pass
BOTH of these, with no exceptions, or it is dropped entirely — it never
reaches the ranking engine, never gets persisted, never shows up in any
tier:

    1. NO-3 score >= 85
    2. Safety score == 100 (perfect safety — any deduction disqualifies it)

Matches that clear this gate are labeled tier "ELITE" (matches the
NO-3: 88.5 | Safety: 100 | Tier: ELITE badge format used in the bot output).
Dominance/odds/form are still computed upstream and stored on the
prediction for context, but they no longer gate inclusion — NO-3 and
Safety are the only two hard requirements now.
"""
from app.services.scoring_types import MatchContext

NO3_PASS_THRESHOLD = 85.0
SAFETY_PASS_THRESHOLD = 100.0


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
