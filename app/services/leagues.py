"""
PHASE 5 — League scanning rules.

SCAN_ALL_LEAGUES = True  →  scan every competition by default.
Top-tier leagues are explicitly whitelisted so they are NEVER accidentally
excluded by future keyword changes. The REJECT_KEYWORDS blacklist filters
out youth / reserve / women / friendly / qualifier rounds that add noise
without being genuine senior competitive fixtures.
"""

SCAN_ALL_LEAGUES = True

# Explicit top-tier + well-data'd leagues. Used as a reference/allowlist
# when SCAN_ALL_LEAGUES = False, and also logged for informational purposes.
LEAGUE_WHITELIST: dict[int, str] = {
    # England
    39: "Premier League",
    40: "Championship",
    41: "League One",
    42: "League Two",
    # Spain
    140: "La Liga",
    141: "La Liga 2",
    # Germany
    78: "Bundesliga",
    79: "2. Bundesliga",
    3: "3. Liga",
    # Italy
    135: "Serie A",
    136: "Serie B",
    # France
    61: "Ligue 1",
    62: "Ligue 2",
    # Portugal
    94: "Primeira Liga",
    95: "Liga Portugal 2",
    # Netherlands
    88: "Eredivisie",
    89: "Eerste Divisie",
    # Belgium
    144: "Pro League",
    # Turkey
    203: "Süper Lig",
    # Scotland
    179: "Premiership",
    # Brazil
    71: "Série A",
    72: "Série B",
    # Argentina
    128: "Liga Profesional",
    # USA
    253: "MLS",
    # Mexico
    262: "Liga MX",
    # Champions League / Europa / Conference
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    # Ireland
    357: "Premier Division (Ireland)",
}

# League IDs to hard-exclude even in full-scan mode.
# Add IDs here if a specific competition consistently produces noise picks.
EXCLUDED_LEAGUE_IDS: set[int] = set()

# Lowercase substrings that trigger rejection of a league/competition name.
REJECT_KEYWORDS = (
    "friendl",
    "youth",
    "u15", "u16", "u17", "u18", "u19", "u20", "u21", "u23",
    "reserve", "reserves",
    "women", "ladies", "female",
    "amateur",
    "futsal",
    "beach",
    "indoor",
)


def is_allowed_league(league_id: int, league_name: str) -> bool:
    """Return True if this league should be included in the daily scan."""
    lname = (league_name or "").lower()

    if league_id in EXCLUDED_LEAGUE_IDS:
        return False
    if any(k in lname for k in REJECT_KEYWORDS):
        return False

    if not SCAN_ALL_LEAGUES:
        return league_id in LEAGUE_WHITELIST

    return True
