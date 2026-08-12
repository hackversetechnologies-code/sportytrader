"""
Async API-Football client.

Handles:
  - Auth headers
  - Rate limiting to stay under the Pro plan's 300/min (5 req/sec) ceiling
  - A soft daily budget guard (7,500/day) backed by Redis so a crash/restart
    doesn't reset the counter mid-day
  - Retries with backoff on transient failures (429 / 5xx / network errors)
"""
import asyncio
import time
from datetime import date, datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    pass


class ApiFootballClient:
    """
    Simple token-bucket limiter for the per-second cap, plus a Redis-backed
    daily counter. One instance should be shared/reused across the app.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._lock = asyncio.Lock()
        self._min_interval = 1.0 / settings.api_football_max_per_second
        self._last_call = 0.0
        self._client = httpx.AsyncClient(
            base_url=settings.api_football_base_url,
            headers={"x-apisports-key": settings.api_football_key},
            timeout=20.0,
        )

    async def close(self):
        await self._client.aclose()

    async def _throttle(self):
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()

    async def _check_daily_budget(self):
        if self._redis is None:
            return
        key = f"apifootball:calls:{date.today().isoformat()}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 60 * 60 * 30)  # ~30h safety TTL
        if count > settings.api_football_max_per_day:
            raise RateLimitExceeded(
                f"Daily API-Football budget of {settings.api_football_max_per_day} exceeded."
            )
        if count > settings.api_football_max_per_day * 0.9:
            logger.warning("API-Football daily budget at %s/%s calls", count, settings.api_football_max_per_day)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError, RateLimitExceeded)),
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        await self._check_daily_budget()
        await self._throttle()
        resp = await self._client.get(path, params=params or {})
        if resp.status_code == 429:
            logger.warning("Hit HTTP 429 from API-Football, backing off...")
            await asyncio.sleep(4)
            raise RateLimitExceeded("Hit 429 rate limit from API-Football")
        resp.raise_for_status()
        data = resp.json()
        errors = data.get("errors")
        if errors:
            if isinstance(errors, dict) and "rateLimit" in errors:
                logger.warning("Hit API-Football rateLimit in response: %s. Backing off...", errors["rateLimit"])
                await asyncio.sleep(4)
                raise RateLimitExceeded(f"Rate limited by API-Football: {errors['rateLimit']}")
            logger.warning("API-Football returned errors for %s: %s", path, errors)
        return data

    # ---- Endpoints used by the pipeline (PHASE 4 / PHASE 6) ----

    async def get_fixtures_by_date(self, day: date, timezone: str) -> list[dict]:
        data = await self._get("/fixtures", {"date": day.isoformat(), "timezone": timezone})
        return data.get("response", [])

    async def get_standings(self, league_id: int, season: int) -> list[dict]:
        data = await self._get("/standings", {"league": league_id, "season": season})
        return data.get("response", [])

    async def get_team_statistics(self, team_id: int, league_id: int, season: int) -> dict:
        data = await self._get(
            "/teams/statistics",
            {"team": team_id, "league": league_id, "season": season},
        )
        resp = data.get("response")
        return resp or {}

    async def get_h2h(self, home_id: int, away_id: int, last: int = 10) -> list[dict]:
        data = await self._get("/fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": last})
        return data.get("response", [])

    async def get_injuries(self, fixture_id: int) -> list[dict]:
        data = await self._get("/injuries", {"fixture": fixture_id})
        return data.get("response", [])

    async def get_odds(self, fixture_id: int) -> list[dict]:
        data = await self._get("/odds", {"fixture": fixture_id})
        return data.get("response", [])

    async def get_lineups(self, fixture_id: int) -> list[dict]:
        data = await self._get("/fixtures/lineups", {"fixture": fixture_id})
        return data.get("response", [])

    async def get_fixture_events(self, fixture_id: int) -> list[dict]:
        """Used for the early-goal filter (goal minute timing)."""
        data = await self._get("/fixtures/events", {"fixture": fixture_id})
        return data.get("response", [])

    async def get_fixture_by_id(self, fixture_id: int) -> dict | None:
        """Single-fixture lookup — used by the pre-kickoff recheck to catch
        status changes (postponed/cancelled/etc.) after a match already
        passed scoring."""
        data = await self._get("/fixtures", {"id": fixture_id})
        response = data.get("response", [])
        return response[0] if response else None
