"""
Database models — mirrors the PHASE 2 schema from the framework, plus a
MatchResult table used by the learning system (PHASE 18).
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    league_name: Mapped[str] = mapped_column(String(128))
    home_team_id: Mapped[int] = mapped_column(Integer)
    home_team: Mapped[str] = mapped_column(String(128))
    away_team_id: Mapped[int] = mapped_column(Integer)
    away_team: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="NS")  # NS, LIVE, FT, etc.
    season: Mapped[int] = mapped_column(Integer, default=0)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TeamStatistics(Base):
    __tablename__ = "team_statistics"
    __table_args__ = (UniqueConstraint("team_id", "league_id", "season", name="uq_team_league_season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, index=True)
    league_id: Mapped[int] = mapped_column(Integer, index=True)
    season: Mapped[int] = mapped_column(Integer)

    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)

    goals_scored: Mapped[int] = mapped_column(Integer, default=0)
    goals_conceded: Mapped[int] = mapped_column(Integer, default=0)

    home_wins: Mapped[int] = mapped_column(Integer, default=0)
    home_draws: Mapped[int] = mapped_column(Integer, default=0)
    home_losses: Mapped[int] = mapped_column(Integer, default=0)

    away_wins: Mapped[int] = mapped_column(Integer, default=0)
    away_draws: Mapped[int] = mapped_column(Integer, default=0)
    away_losses: Mapped[int] = mapped_column(Integer, default=0)

    clean_sheets: Mapped[int] = mapped_column(Integer, default=0)
    failed_to_score: Mapped[int] = mapped_column(Integer, default=0)

    matches_played: Mapped[int] = mapped_column(Integer, default=0)

    # last-5 form data, stored as comma string e.g. "W,W,D,L,W"
    form: Mapped[str | None] = mapped_column(String(32), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class H2HRecord(Base):
    __tablename__ = "h2h_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    home_team_id: Mapped[int] = mapped_column(Integer, index=True)
    away_team_id: Mapped[int] = mapped_column(Integer, index=True)
    home_team: Mapped[str] = mapped_column(String(128))
    away_team: Mapped[str] = mapped_column(String(128))

    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    home_goals: Mapped[int] = mapped_column(Integer, default=0)
    away_goals: Mapped[int] = mapped_column(Integer, default=0)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    home_team: Mapped[str] = mapped_column(String(128))
    away_team: Mapped[str] = mapped_column(String(128))
    league_name: Mapped[str] = mapped_column(String(128))
    kickoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    no3_score: Mapped[float] = mapped_column(Float, default=0.0)
    dominance_score: Mapped[float] = mapped_column(Float, default=0.0)
    safety_score: Mapped[float] = mapped_column(Float, default=0.0)

    passed_consensus: Mapped[bool] = mapped_column(Boolean, default=False)
    consensus_votes: Mapped[int] = mapped_column(Integer, default=0)

    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(16), nullable=True)  # TOP20/TOP10/TOP6/TOP3/TOP2/LOCK

    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    removed_at_recheck: Mapped[bool] = mapped_column(Boolean, default=False)

    result: Mapped[str | None] = mapped_column(String(16), nullable=True)  # WON/FAILED/PENDING
    final_score: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class MatchResult(Base):
    """PHASE 18 — learning system log, one row per settled prediction."""
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(BigInteger, index=True)
    match_label: Mapped[str] = mapped_column(String(256))
    league_name: Mapped[str] = mapped_column(String(128))
    prediction: Mapped[str] = mapped_column(String(32), default="NO-3")
    result: Mapped[str] = mapped_column(String(16))  # WON / FAILED
    final_score: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    no3_score: Mapped[float] = mapped_column(Float, default=0.0)
    safety_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TelegramUser(Base):
    """Subscribed Telegram users for daily broadcast."""
    __tablename__ = "telegram_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
