# NO-3 Telegram Bot

Automated football-fixture screening system: pulls fixtures from API-Football,
runs them through the NO-3 / Dominance / Safety / Consensus pipeline, ranks
survivors, and pushes results to Telegram. Built with FastAPI, PostgreSQL,
Redis, Aiogram and APScheduler.

## What's implemented vs. what needs your input

This is a complete, runnable skeleton that implements every phase of the
framework (fixture discovery across **every competition returned for the
day** — not a narrow whitelist, league filtering, data collection, feature
engineering, all five reject filters*, Dominance/NO-3/Safety/Consensus/
Ranking engines, Telegram commands, the daily scheduler, the pre-kickoff
recheck, and the learning system). Three things are deliberately left as
config/extension points rather than guessed at, because getting them wrong
silently would be worse than flagging them:

1. **League exclusions** — `app/services/leagues.py` scans every league by
   default (`SCAN_ALL_LEAGUES = True`) and only blocks non-competitive
   fixture types (friendlies, youth, women's, reserves) by name-matching.
   If you ever find a specific league you want hard-blocked, add its ID to
   `EXCLUDED_LEAGUE_IDS`.
2. **Goal-explosion filter (PHASE 9)** — needs a per-match goals log (last 5
   fixtures per team) to check "scored/conceded 4+ twice in 5 games"
   precisely. The stub in `app/services/filters.py` is wired into the
   pipeline and documents exactly which endpoint call to add
   (`/fixtures?team={id}&last=5`).
3. **Motivation score (PHASE 11/12)** — currently a flat placeholder. Wire it
   to standings proximity (relegation/promotion/European qualification
   zones) once you're pulling `/standings` into the pipeline.

## Full-day, every-competition scanning

`discover_fixtures` pulls **every** fixture the API returns for the target
date, across every league — not a curated shortlist. Two hard filters run
before anything reaches scoring:

- **League/type filter** — excludes only genuinely non-competitive matches
  (friendlies, youth, women's, reserve sides) by name match; real
  competitions of every tier are scanned by default.
- **Status filter** — a match must be in `NS` (Not Started / scheduled)
  status to be scored at all. Anything cancelled, postponed, TBD,
  abandoned, suspended, interrupted, already live, or already finished by
  the time the scan runs is **hard rejected** — it's never added to any
  tier, never shows up in `/today`, `/top6`, etc. This is enforced twice:
  once at daily discovery, and again during the PHASE 17 pre-kickoff
  recheck, so a match that gets postponed *after* it already passed
  scoring is pulled before kickoff instead of lingering as a stale pick.

Because a full-day scan across every league can mean hundreds of fixtures,
`run_daily_pipeline` processes fixtures **concurrently** (default 20 at a
time, tunable via `PIPELINE_CONCURRENCY` in `pipeline.py`). The
`ApiFootballClient`'s own rate limiter still throttles the actual HTTP
calls to your Pro-plan cap (5 req/sec, 7,500/day) — concurrency just keeps
that limiter fed instead of idling, so the pipeline finishes fast without
ever exceeding your quota. With that said: scanning literally every match
worldwide every day *will* consume a meaningfully larger share of your
7,500/day budget than a 7-league shortlist did — team-statistics and H2H
results are cached in Postgres for ~20 hours precisely to keep this
sustainable, but if you regularly see hundreds of fixtures a day it's
worth watching the `/health`-adjacent logs for the daily-budget warning
that fires at 90% usage.

Everything else — scoring formulas, weights, thresholds, tier cutoffs — is
implemented exactly to the spec numbers you gave (25/20/20/10/5/5/10/5 for
NO-3, 40/20/20/10/10 for Dominance, the NO-3 ≥ 85 / Safety = 100 hard gate,
etc.) so you can tune constants without hunting for where they live.

## Project layout

```
app/
  config.py          # env-driven settings
  database.py         # async SQLAlchemy engine/session
  models.py            # Fixtures, TeamStatistics, H2H, Predictions, MatchResults
  api_football.py       # rate-limited API-Football client (5 req/sec, 7500/day guard)
  services/
    leagues.py            # PHASE 5 whitelist
    fixtures.py            # PHASE 4 discovery
    collection.py           # PHASE 6 data collection
    features.py              # PHASE 7 feature engineering
    filters.py                # PHASE 8-10 reject filters
    dominance.py                # PHASE 11
    no3_engine.py                 # PHASE 12
    safety.py                      # PHASE 13
    consensus.py                    # PHASE 14
    ranking.py                       # PHASE 15
    pipeline.py                       # orchestrates all of the above
    recheck.py                         # PHASE 17 pre-kickoff recheck
    learning.py                         # PHASE 18
  bot/
    bot.py       # aiogram Bot/Dispatcher
    handlers.py   # /start /today /tomorrow /top6 /top3 /top2 /lock
    formatting.py  # Telegram message templates
  scheduler.py   # APScheduler: midnight pipeline + recheck interval
  main.py          # FastAPI app, wires bot polling + scheduler together
```

## Local setup

```bash
cp .env.example .env
# edit .env: API_FOOTBALL_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DATABASE_URL, REDIS_URL
docker compose up -d --build
```

That's it — Postgres, Redis and the bot all start together, tables are
created automatically on first boot, the scheduler starts the daily pipeline
at `DAILY_RUN_HOUR:DAILY_RUN_MINUTE` (default 00:05 in your configured
timezone), and the bot begins polling Telegram immediately.

Check it's alive:
```bash
curl http://localhost:8000/health
```

Trigger the pipeline manually instead of waiting for the cron job:
```bash
curl -X POST http://localhost:8000/pipeline/run
```

## Deploying to a Contabo VPS (Ubuntu)

1. **Point a domain or just use the IP** — not required for a Telegram bot
   (it doesn't need inbound webhooks unless you switch off polling later).

2. **SSH in and install Docker:**
   ```bash
   ssh root@your-vps-ip
   curl -fsSL https://get.docker.com | sh
   apt install -y docker-compose-plugin
   ```

3. **Copy the project up** (from your machine):
   ```bash
   scp -r no3bot root@your-vps-ip:/opt/no3bot
   ```

4. **Configure and launch:**
   ```bash
   ssh root@your-vps-ip
   cd /opt/no3bot
   cp .env.example .env
   nano .env   # fill in real values
   docker compose up -d --build
   ```

5. **Confirm it's running:**
   ```bash
   docker compose ps
   docker compose logs -f bot
   ```

6. **Auto-restart on reboot** is already handled by `restart: unless-stopped`
   in `docker-compose.yml`.

7. **Updating later:**
   ```bash
   cd /opt/no3bot
   git pull            # or scp the changed files up again
   docker compose up -d --build
   ```

## Getting your credentials

- **API-Football Pro key:** dashboard.api-football.com → API Keys.
- **Telegram bot token:** message @BotFather → `/newbot`.
- **Telegram chat/channel ID:** add your bot to the target channel as admin,
  post any message, then hit
  `https://api.telegram.org/bot<TOKEN>/getUpdates` to read the chat ID.

## Rate limits

The API-Football client throttles itself to 5 requests/sec and tracks a
Redis-backed daily counter capped at 7,500 — both configurable in
`app/config.py`. Team-statistics and H2H results are cached in Postgres and
only re-fetched once per ~20 hours, so a normal day's pipeline run for a
few dozen fixtures uses a small fraction of the daily budget.

## Extending

- Standings ingestion (`/standings`) isn't wired into the pipeline yet — add
  a `collect_standings` call in `collection.py` if you want position-based
  motivation scoring or an explicit "League Position Difference" feature.
- Card-risk and lineup-based safety deductions are stubbed as function
  parameters (`high_card_risk`, `odds_moved_sharply` in `safety.py` /
  `recheck.py`) — plug in real detection once you decide the exact signal
  (e.g. average cards/match from `/fixtures/statistics`).
