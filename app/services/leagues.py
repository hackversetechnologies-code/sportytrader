"""
PHASE 5 — League scanning rules.

Scanning includes priority support for requested target leagues:
1. Argentina Primera (Liga Profesional)
2. Uruguay Primera
3. Paraguay Primera
4. Morocco Botola
5. Algeria Ligue 1
6. Tunisia Ligue 1
7. South Africa PSL
8. Portugal Primeira Liga
9. Italy Serie B
10. France Ligue 2
11. Romania Liga I
12. Serbia SuperLiga
13. Bulgaria First League
14. Brazil Serie B
15. Nigeria Premier League
16. Slovenia PrvaLiga
17. Slovakia Super Liga
18. Czech First League
19. Additional competitive leagues
20. Paraguay - Division Intermedia
21. Russia - Premier League
22. Eerste Divisie
23. UEFA Champions League
24. Cupa României
25. CONMEBOL Libertadores

SCAN_ALL_LEAGUES = True  →  scans every senior competitive match while rejecting youth/reserve/friendlies/women's fixtures.
"""

SCAN_ALL_LEAGUES = False

# Whitelisted / Target League IDs (API-Football IDs)
TARGET_LEAGUE_IDS: dict[int, str] = {
    # 1. Argentina Primera
    128: "Liga Profesional",
    # 2. Uruguay Primera
    268: "Primera División",
    # 3. Paraguay Primera
    250: "Division Profesional",
    # 4. Morocco Botola
    200: "Botola Pro",
    # 5. Algeria Ligue 1
    186: "Ligue 1",
    # 6. Tunisia Ligue 1
    202: "Ligue 1",
    # 7. South Africa PSL
    288: "Premier League",
    # 8. Portugal Primeira Liga
    94: "Primeira Liga",
    # 9. Italy Serie B
    136: "Serie B",
    # 10. France Ligue 2
    62: "Ligue 2",
    # 11. Romania Liga I
    283: "Liga I",
    # 12. Serbia SuperLiga
    286: "SuperLiga",
    # 13. Bulgaria First League
    172: "First League",
    # 14. Brazil Serie B
    72: "Série B",
    # 15. Nigeria Premier League
    396: "NPFL",
    # 16. Slovenia PrvaLiga
    373: "1. SNL",
    # 17. Slovakia Super Liga
    332: "Super Liga",
    # 18. Czech First League
    345: "First League",
    # 20. Paraguay Division Intermedia
    252: "Division Intermedia",
    # 21. Russia Premier League
    235: "Premier League",
    # 22. Eerste Divisie
    89: "Eerste Divisie",
    # 23. UEFA Champions League
    2: "UEFA Champions League",
    # 24. Cupa României
    546: "Cupa României",
    # 25. CONMEBOL Libertadores
    13: "CONMEBOL Libertadores",
}

LEAGUE_WHITELIST: dict[int, str] = {
    **TARGET_LEAGUE_IDS,
    # Major Europe & Worldwide SportyBet Mainstream Leagues
    39: "Premier League",
    40: "Championship",
    41: "League One",
    140: "La Liga",
    141: "La Liga 2",
    78: "Bundesliga",
    79: "2. Bundesliga",
    135: "Serie A",
    61: "Ligue 1",
    71: "Série A (Brazil)",
    88: "Eredivisie",
    144: "Pro League (Belgium)",
    203: "Süper Lig (Turkey)",
    179: "Premiership (Scotland)",
    307: "Saudi Pro League",
    253: "MLS",
    262: "Liga MX",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    11: "CONMEBOL Sudamericana",
}

# League IDs to hard-exclude
EXCLUDED_LEAGUE_IDS: set[int] = set()

# Lowercase substrings that trigger rejection of non-senior competitive fixtures
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
