"""
PHASE 5 — Strict SportyBet Mainstream League scanning rules.

Exact 40 requested top-flight leagues and major continental tournaments:

South America:
  1. Argentina Primera (Liga Profesional - 128)
  2. Uruguay Primera (268)
  3. Paraguay Primera (Division Profesional - 250)
  4. Brazil Série A (71)
  5. Colombia Primera A (239)
  6. Chile Primera (265)
  7. Peru Liga 1 (281)

Europe:
  8. England Premier League (39)
  9. Spain LaLiga (140)
  10. Italy Serie A (135)
  11. Germany Bundesliga (78)
  12. France Ligue 1 (61)
  13. Portugal Primeira Liga (94)
  14. Netherlands Eredivisie (88)
  15. Belgium Pro League (144)
  16. Scotland Premiership (179)
  17. Turkey Süper Lig (203)
  18. Romania Liga I (283)
  19. Serbia SuperLiga (286)
  20. Bulgaria First League (172)
  21. Slovenia PrvaLiga (373)
  22. Slovakia Super Liga (332)
  23. Czech First League (345)
  24. Russia Premier League (235)

Africa:
  25. Morocco Botola (200)
  26. Algeria Ligue 1 (186)
  27. Tunisia Ligue 1 (202)
  28. South Africa PSL (288)
  29. Nigeria Premier League (396)

North America & Asia:
  30. USA MLS (253)
  31. Mexico Liga MX (262)
  32. Japan J1 League (98)
  33. South Korea K-League 1 (292)
  34. Saudi Pro League (307)

Major Continental Tournaments:
  35. UEFA Champions League (2)
  36. UEFA Europa League (3)
  37. UEFA Conference League (848)
  38. CONMEBOL Libertadores (13)
  39. CONMEBOL Sudamericana (11)
  40. AFC Champions League Elite (17)
"""

SCAN_ALL_LEAGUES = False

# Whitelisted 40 SportyBet Mainstream League IDs (API-Football IDs)
TARGET_LEAGUE_IDS: dict[int, str] = {
    # South America
    128: "Argentina - Liga Profesional",
    268: "Uruguay - Primera División",
    250: "Paraguay - Division Profesional",
    71: "Brazil - Série A",
    239: "Colombia - Primera A",
    265: "Chile - Primera División",
    281: "Peru - Liga 1",

    # Europe
    39: "England - Premier League",
    140: "Spain - LaLiga",
    135: "Italy - Serie A",
    78: "Germany - Bundesliga",
    61: "France - Ligue 1",
    94: "Portugal - Primeira Liga",
    88: "Netherlands - Eredivisie",
    144: "Belgium - Pro League",
    179: "Scotland - Premiership",
    203: "Turkey - Süper Lig",
    283: "Romania - Liga I",
    286: "Serbia - SuperLiga",
    172: "Bulgaria - First League",
    373: "Slovenia - PrvaLiga",
    332: "Slovakia - Super Liga",
    345: "Czech Republic - First League",
    235: "Russia - Premier League",

    # Africa
    200: "Morocco - Botola Pro",
    186: "Algeria - Ligue 1",
    202: "Tunisia - Ligue 1",
    288: "South Africa - Premier Soccer League",
    396: "Nigeria - NPFL",

    # North America & Asia
    253: "USA - MLS",
    262: "Mexico - Liga MX",
    98: "Japan - J1 League",
    292: "South Korea - K League 1",
    307: "Saudi Arabia - Saudi Pro League",

    # Major Continental Tournaments
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    13: "CONMEBOL Libertadores",
    11: "CONMEBOL Sudamericana",
    17: "AFC Champions League Elite",
}

LEAGUE_WHITELIST: dict[int, str] = dict(TARGET_LEAGUE_IDS)

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
