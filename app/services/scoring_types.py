"""Shared data structures passed between the scoring engines (PHASE 7-15)."""
from dataclasses import dataclass, field

from app.models import Fixture, H2HRecord, TeamStatistics


@dataclass
class MatchContext:
    fixture: Fixture
    home_stats: TeamStatistics | None
    away_stats: TeamStatistics | None
    h2h: list[H2HRecord]
    odds: list[dict]
    home_events: list[dict] = field(default_factory=list)
    away_events: list[dict] = field(default_factory=list)
    injuries: list[dict] = field(default_factory=list)
    lineups: list[dict] = field(default_factory=list)

    # PHASE 7 feature outputs (0-100)
    strength_gap: float = 0.0
    attack_gap: float = 0.0
    defense_gap: float = 0.0
    home_away_balance: float = 0.0

    # PHASE 8-10 filter outputs
    rejected: bool = False
    rejected_reason: str | None = None
    early_goal_risk: float = 0.0

    # PHASE 11-13 engine outputs
    dominance_score: float = 0.0
    no3_score: float = 0.0
    safety_score: float = 0.0

    # PHASE 14
    passed_consensus: bool = False
    consensus_votes: int = 0

    def reject(self, reason: str) -> None:
        self.rejected = True
        self.rejected_reason = reason
