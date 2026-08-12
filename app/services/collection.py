"""
PHASE 6 — Data collection.

For every kept fixture, pull standings-derived team statistics, H2H,
injuries, odds and (close to kickoff) lineups. Statistics and H2H are
cached in Postgres so we don't re-fetch on every pipeline run for teams
we already have fresh data for.

Each DB-touching helper opens and manages its own short-lived AsyncSession
rather than accepting one from the caller. This matters for speed: an
AsyncSession is NOT safe to use concurrently from multiple coroutines, and
collect_all_for_fixture runs statistics/H2H/odds calls in parallel via
asyncio.gather — sharing one session across that gather would corrupt
state or throw under load. Self-contained sessions make the concurrency
in pipeline.py actually safe instead of just fast-looking.
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.api_football import ApiFootballClient
from app.database import async_session, get_insert_stmt
from app.logger import get_logger
from app.models import Fixture, H2HRecord, TeamStatistics

logger = get_logger(__name__)

STATS_FRESHNESS = timedelta(hours=20)  # re-pull team stats at most once/day


def _parse_statistics_payload(payload: dict) -> dict:
    fixtures = payload.get("fixtures", {})
    goals = payload.get("goals", {})
    clean_sheet = payload.get("clean_sheet", {})
    failed_to_score = payload.get("failed_to_score", {})
    form = payload.get("form") or ""

    return dict(
        wins=fixtures.get("wins", {}).get("total", 0) or 0,
        draws=fixtures.get("draws", {}).get("total", 0) or 0,
        losses=fixtures.get("loses", {}).get("total", 0) or 0,
        home_wins=fixtures.get("wins", {}).get("home", 0) or 0,
        away_wins=fixtures.get("wins", {}).get("away", 0) or 0,
        home_draws=fixtures.get("draws", {}).get("home", 0) or 0,
        away_draws=fixtures.get("draws", {}).get("away", 0) or 0,
        home_losses=fixtures.get("loses", {}).get("home", 0) or 0,
        away_losses=fixtures.get("loses", {}).get("away", 0) or 0,
        goals_scored=goals.get("for", {}).get("total", {}).get("total", 0) or 0,
        goals_conceded=goals.get("against", {}).get("total", {}).get("total", 0) or 0,
        clean_sheets=clean_sheet.get("total", 0) or 0,
        failed_to_score=failed_to_score.get("total", 0) or 0,
        matches_played=fixtures.get("played", {}).get("total", 0) or 0,
        form=form[-5:] if form else None,
    )


async def collect_team_statistics(
    client: ApiFootballClient, team_id: int, league_id: int, season: int
) -> TeamStatistics | None:
    async with async_session() as session:
        result = await session.execute(
            select(TeamStatistics).where(
                TeamStatistics.team_id == team_id,
                TeamStatistics.league_id == league_id,
                TeamStatistics.season == season,
            )
        )
        cached = result.scalar_one_or_none()
        if cached and (datetime.utcnow() - cached.updated_at) < STATS_FRESHNESS:
            return cached

        payload = await client.get_team_statistics(team_id, league_id, season)
        if not payload:
            logger.warning("No statistics returned for team %s league %s season %s", team_id, league_id, season)
            return cached  # fall back to stale cache rather than nothing, if we have it

        parsed = _parse_statistics_payload(payload)
        stmt = get_insert_stmt(TeamStatistics).values(team_id=team_id, league_id=league_id, season=season, **parsed)
        stmt = stmt.on_conflict_do_update(
            index_elements=["team_id", "league_id", "season"],
            set_={**{k: stmt.excluded[k] for k in parsed}, "updated_at": datetime.utcnow()},
        )
        await session.execute(stmt)
        await session.commit()

        result = await session.execute(
            select(TeamStatistics).where(
                TeamStatistics.team_id == team_id,
                TeamStatistics.league_id == league_id,
                TeamStatistics.season == season,
            )
        )
        return result.scalar_one_or_none()


async def collect_h2h(
    client: ApiFootballClient, home_id: int, away_id: int,
    home_name: str, away_name: str, last: int = 10,
) -> list[H2HRecord]:
    async with async_session() as session:
        result = await session.execute(
            select(H2HRecord).where(
                H2HRecord.home_team_id == home_id, H2HRecord.away_team_id == away_id
            ).order_by(H2HRecord.match_date.desc()).limit(last)
        )
        existing = list(result.scalars().all())
        if len(existing) >= last:
            return existing

        raw = await client.get_h2h(home_id, away_id, last=last)
        for item in raw:
            fixture_info = item.get("fixture", {})
            goals = item.get("goals", {})
            try:
                match_date = datetime.fromisoformat(fixture_info.get("date"))
            except (TypeError, ValueError):
                continue
            stmt = get_insert_stmt(H2HRecord).values(
                home_team_id=home_id,
                away_team_id=away_id,
                home_team=home_name,
                away_team=away_name,
                match_date=match_date,
                home_goals=goals.get("home") or 0,
                away_goals=goals.get("away") or 0,
            )
            await session.execute(stmt)
        await session.commit()

        result = await session.execute(
            select(H2HRecord).where(
                H2HRecord.home_team_id == home_id, H2HRecord.away_team_id == away_id
            ).order_by(H2HRecord.match_date.desc()).limit(last)
        )
        return list(result.scalars().all())


async def collect_injuries(client: ApiFootballClient, fixture_id: int) -> list[dict]:
    return await client.get_injuries(fixture_id)


async def collect_odds(client: ApiFootballClient, fixture_id: int) -> list[dict]:
    return await client.get_odds(fixture_id)


async def collect_lineups(client: ApiFootballClient, fixture_id: int) -> list[dict]:
    """Lineups are only populated by the API close to kickoff — call this
    from the PHASE 17 pre-kickoff recheck, not the daily pipeline."""
    return await client.get_lineups(fixture_id)


async def collect_all_for_fixture(client: ApiFootballClient, fixture: Fixture) -> dict:
    """
    Gather everything the feature engineering step needs for one fixture.
    Safe to run concurrently across many fixtures at once (see
    app/services/pipeline.py) — every DB-touching call here manages its
    own session, and none of the four calls below share state with each
    other either, so this whole function is concurrency-safe end to end.
    """
    home_stats, away_stats, h2h, odds = await asyncio.gather(
        collect_team_statistics(client, fixture.home_team_id, fixture.league_id, fixture.season),
        collect_team_statistics(client, fixture.away_team_id, fixture.league_id, fixture.season),
        collect_h2h(client, fixture.home_team_id, fixture.away_team_id, fixture.home_team, fixture.away_team),
        collect_odds(client, fixture.fixture_id),
    )
    return {
        "fixture": fixture,
        "home_stats": home_stats,
        "away_stats": away_stats,
        "h2h": h2h,
        "odds": odds,
    }
