"""
PHASE 4 + PHASE 5 — Fixture discovery, full-competition scan, and the
match-status hard filter.

Every fixture the API returns for the day is pulled (not a handful of
leagues) and upserted so status changes are always tracked. Only fixtures
still in "Not Started" (NS) state make it into the list that gets scored —
cancelled, postponed, TBD, abandoned, walkover, suspended, or otherwise
not-actually-being-played fixtures are hard rejected and never reach the
scoring pipeline, even if they were previously stored as a normal
scheduled match and only flipped status afterward (a rediscovery run
always refreshes status before deciding what's included).
"""
import json
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_football import ApiFootballClient
from app.database import get_insert_stmt
from app.logger import get_logger
from app.models import Fixture
from app.services.leagues import is_allowed_league

logger = get_logger(__name__)

# API-Football short status codes. Only "NS" (Not Started / scheduled) is
# eligible for scoring. Everything else here means the match is not going
# to be played as originally scheduled (or isn't a pre-match state at all)
# and must be hard rejected.
PLAYABLE_STATUS = "NS"

HARD_REJECT_STATUSES = {
    "TBD": "Time To Be Defined",
    "PST": "Postponed",
    "CANC": "Cancelled",
    "ABD": "Abandoned",
    "AWD": "Technical loss / Awarded",
    "WO": "Walkover",
    "SUSP": "Suspended",
    "INT": "Interrupted",
    # already in progress or finished by the time we scanned — not a
    # pre-match pick candidate either
    "1H": "Already in progress (1st half)",
    "HT": "Already in progress (half-time)",
    "2H": "Already in progress (2nd half)",
    "ET": "Already in progress (extra time)",
    "P": "Already in progress (penalties)",
    "LIVE": "Already live",
    "FT": "Already finished",
    "AET": "Already finished (after extra time)",
    "PEN": "Already finished (after penalties)",
}


async def discover_fixtures(
    session: AsyncSession, client: ApiFootballClient, target_day: date, timezone: str
) -> list[Fixture]:
    """
    Pull EVERY fixture for target_day across every competition, upsert them
    all (so status transitions are always current), and return only the
    ones that are still genuinely scheduled to be played (status == NS).
    """
    raw_fixtures = await client.get_fixtures_by_date(target_day, timezone)
    total_seen = len(raw_fixtures)
    league_rejected = 0
    status_rejected = 0

    for item in raw_fixtures:
        league = item.get("league", {})
        teams = item.get("teams", {})
        fixture_info = item.get("fixture", {})

        league_id = league.get("id")
        league_name = league.get("name", "")

        if not is_allowed_league(league_id, league_name):
            league_rejected += 1
            continue

        fixture_id = fixture_info.get("id")
        kickoff_raw = fixture_info.get("date")
        try:
            kickoff = datetime.fromisoformat(kickoff_raw)
        except (TypeError, ValueError):
            logger.warning("Skipping fixture %s with bad date %s", fixture_id, kickoff_raw)
            continue

        status_short = fixture_info.get("status", {}).get("short", "NS")
        if status_short in HARD_REJECT_STATUSES:
            status_rejected += 1
            logger.info(
                "Hard rejecting fixture %s (%s vs %s): status=%s (%s)",
                fixture_id,
                teams.get("home", {}).get("name"),
                teams.get("away", {}).get("name"),
                status_short,
                HARD_REJECT_STATUSES[status_short],
            )

        # Always upsert — even hard-rejected fixtures get their status
        # refreshed in the DB, so a match that goes NS -> PST is correctly
        # excluded on the next scan instead of lingering as stale "NS".
        stmt = get_insert_stmt(Fixture).values(
            fixture_id=fixture_id,
            date=kickoff,
            league_id=league_id,
            league_name=league_name,
            home_team_id=teams.get("home", {}).get("id"),
            home_team=teams.get("home", {}).get("name"),
            away_team_id=teams.get("away", {}).get("id"),
            away_team=teams.get("away", {}).get("name"),
            status=status_short,
            season=league.get("season", 0),
            raw_json=json.dumps(item),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["fixture_id"],
            set_={
                "date": stmt.excluded.date,
                "status": stmt.excluded.status,
                "raw_json": stmt.excluded.raw_json,
            },
        )
        await session.execute(stmt)

    await session.commit()

    result = await session.execute(
        select(Fixture).where(
            Fixture.date >= datetime.combine(target_day, datetime.min.time()),
            Fixture.date < datetime.combine(target_day + timedelta(days=1), datetime.min.time()),
            Fixture.status == PLAYABLE_STATUS,
        )
    )
    kept = list(result.scalars().all())
    logger.info(
        "Fixture scan for %s: %s total seen, %s rejected (league/type), %s rejected (status), %s eligible for scoring",
        target_day, total_seen, league_rejected, status_rejected, len(kept),
    )
    return kept
