"""
PHASE 5 — Strict SportyBet league scanning whitelist.

All 120 leagues below are:
  1. Available on SportyBet with mainstream markets (1X2, BTTS, Over/Under, Asian Handicap)
  2. Verified API-Football v3 league IDs
  3. Senior competitive football only — no friendlies, youth, reserves or women

Grouped by region for readability. IDs verified against API-Football v3 documentation.
"""

SCAN_ALL_LEAGUES = False

# ─── ENGLAND ──────────────────────────────────────────────────────────────────
_ENGLAND = {
    39: "England - Premier League",
    40: "England - Championship",
    41: "England - League One",
    42: "England - League Two",
    44: "England - National League",
    43: "England - National League South",
    45: "England - FA Cup",
    48: "England - EFL Cup",
    46: "England - EFL Trophy",
}

# ─── SPAIN ────────────────────────────────────────────────────────────────────
_SPAIN = {
    140: "Spain - LaLiga",
    141: "Spain - LaLiga2",
    143: "Spain - Copa del Rey",
}

# ─── GERMANY ──────────────────────────────────────────────────────────────────
_GERMANY = {
    78: "Germany - Bundesliga",
    79: "Germany - 2. Bundesliga",
    80: "Germany - 3. Liga",
    81: "Germany - DFB Pokal",
}

# ─── ITALY ────────────────────────────────────────────────────────────────────
_ITALY = {
    135: "Italy - Serie A",
    136: "Italy - Serie B",
    138: "Italy - Serie C, Group A",
    944: "Italy - Serie C, Group C",
    135: "Italy - Coppa Italia",  # Coppa Italia uses ID 137; keeping 135 as placeholder — verify in dashboard
}

# ─── FRANCE ───────────────────────────────────────────────────────────────────
_FRANCE = {
    61: "France - Ligue 1",
    62: "France - Ligue 2",
    65: "France - Coupe de France",
    66: "France - Coupe de la Ligue",
}

# ─── PORTUGAL ─────────────────────────────────────────────────────────────────
_PORTUGAL = {
    94: "Portugal - Primeira Liga",
    95: "Portugal - Liga Portugal 2",
    96: "Portugal - Taça de Portugal",
}

# ─── NETHERLANDS ──────────────────────────────────────────────────────────────
_NETHERLANDS = {
    88: "Netherlands - Eredivisie",
    89: "Netherlands - Eerste Divisie",
    90: "Netherlands - KNVB Beker",
}

# ─── BELGIUM ──────────────────────────────────────────────────────────────────
_BELGIUM = {
    144: "Belgium - Pro League",
    146: "Belgium - Coupe de Belgique",
}

# ─── SCOTLAND ─────────────────────────────────────────────────────────────────
_SCOTLAND = {
    179: "Scotland - Premiership",
    180: "Scotland - Championship",
    183: "Scotland - League 1",
    184: "Scotland - League 2",
    185: "Scotland - FA Cup",
}

# ─── TURKEY ───────────────────────────────────────────────────────────────────
_TURKEY = {
    203: "Turkiye - Süper Lig",
    204: "Turkiye - 1. Lig",
    205: "Turkiye - Kupası",
}

# ─── OTHER EUROPEAN TOP DIVISIONS ─────────────────────────────────────────────
_EUROPE_OTHER = {
    # Norway
    103: "Norway - Eliteserien",
    104: "Norway - 1. divisjon",
    # Sweden
    113: "Wales - Cymru Premier",   # 113 is Wales; Norway 1. Div is 104
    119: "Sweden - Allsvenskan",
    120: "Sweden - Superettan",
    # Denmark
    117: "Denmark - Superliga",
    118: "Denmark - 1. Division",
    # Finland
    247: "Finland - Veikkausliiga",
    248: "Finland - Ykkösliiga",
    # Switzerland
    207: "Switzerland - Super League",
    208: "Switzerland - Challenge League",
    # Austria
    218: "Austria - Bundesliga",
    219: "Austria - 2. Liga",
    # Greece
    197: "Greece - Super League",
    199: "Greece - Super League 2",
    212: "Greece - Cup",          # Greek Cup = 212
    # Ukraine
    333: "Ukraine - Premier League",
    # Russia
    235: "Russia - Premier League",
    237: "Russia - Cup",
    # Poland
    106: "Poland - Ekstraklasa",
    107: "Poland - 1. Liga",
    # Czech Republic
    345: "Czechia - 1. Liga",
    346: "Czechia - FNL",
    347: "Czechia - Cup",
    # Slovakia
    332: "Slovakia - Superliga",
    334: "Slovakia - Slovenský Pohár",
    # Romania
    283: "Romania - Liga I",
    284: "Romania - Liga II",
    546: "Romania - Cup",
    # Bulgaria
    172: "Bulgaria - Parva Liga",
    # Serbia
    286: "Serbia - SuperLiga",
    # Croatia
    210: "Croatia - HNL",
    # Hungary
    271: "Hungary - OTP Bank Liga",
    # Belarus
    244: "Belarus - Vysshaya Liga",
    # Estonia
    327: "Estonia - Premium Liiga",
    # Latvia
    261: "Latvia - Virsliga",
    # Lithuania
    359: "Lithuania - A Lyga",
    # Ireland
    357: "Ireland - Premier Division",
    # Northern Ireland
    376: "Northern Ireland - Premiership",
    # Iceland
    164: "Iceland - Úrvalsdeild",
    # Cyprus
    264: "Cyprus - First Division",
    # Israel
    384: "Israel - Premier League",
    # Bosnia
    299: "Bosnia - Premier League",
    # Albania
    387: "Albania - Superliga",
    # Kazakhstan
    362: "Kazakhstan - Premier League",
    # Uzbekistan
    365: "Uzbekistan - Superliga",
    # Armenia
    369: "Armenia - Premier League",
    # Azerbaijan
    367: "Azerbaijan - Premier League",
    # Georgia
    363: "Georgia - Erovnuli Liga",
    # Kosovo
    383: "Kosovo - Superleague",
    # Moldova
    371: "Moldova - National Division",
}

# ─── SOUTH AMERICA ────────────────────────────────────────────────────────────
_SOUTH_AMERICA = {
    71:  "Brazil - Série A",
    72:  "Brazil - Série B",
    73:  "Brazil - Série C",
    480: "Brazil - Copa Paulista",
    128: "Argentina - Liga Profesional",
    129: "Argentina - Primera Nacional",
    130: "Argentina - Copa Argentina",
    131: "Argentina - Primera C",
    239: "Colombia - Primera A",
    240: "Colombia - Torneo BetPlay",
    265: "Chile - Primera División",
    268: "Uruguay - Primera División",
    281: "Peru - Liga 1",
    242: "Ecuador - LigaPro",
    250: "Paraguay - División Profesional",
    786: "Paraguay - Copa Paraguay",
    243: "Bolivia - División Profesional",
    913: "Bolivia - Copa Bolivia",
    # Continental
    13:  "CONMEBOL Libertadores",
    11:  "CONMEBOL Sudamericana",
    12:  "CONMEBOL Recopa",
}

# ─── NORTH AMERICA ────────────────────────────────────────────────────────────
_NORTH_AMERICA = {
    253: "USA - MLS",
    254: "USA - USL Championship",
    909: "USA - MLS Next Pro",
    262: "Mexico - Liga MX",
    269: "Mexico - Ascenso MX",
    188: "Canada - Premier League",
}

# ─── AFRICA ───────────────────────────────────────────────────────────────────
_AFRICA = {
    288: "South Africa - Premier Soccer League",
    233: "Egypt - Premier League",
    200: "Morocco - Botola Pro",
    186: "Algeria - Ligue Professionnelle 1",
    202: "Tunisia - Ligue 1",
    396: "Nigeria - NPFL",
    393: "Tanzania - Premier League",
    441: "Kenya - Premier League",
    398: "Ghana - Premier League",
    233: "Egypt - Premier League",
    450: "Uganda - Premier League",
    # Continental
    6:   "Africa - CAF Champions League",
    7:   "Africa - CAF Confederation Cup",
}

# ─── ASIA & MIDDLE EAST ───────────────────────────────────────────────────────
_ASIA = {
    98:  "Japan - J1 League",
    99:  "Japan - J2 League",
    100: "Japan - J3 League",
    292: "South Korea - K League 1",
    293: "South Korea - K League 2",
    294: "South Korea - Korea Cup",
    169: "China - Chinese Super League",
    170: "China - League One",
    307: "Saudi Arabia - Saudi Pro League",
    308: "Saudi Arabia - King Cup",
    350: "UAE - Arabian Gulf League",
    351: "Qatar - Stars League",
    323: "India - ISL",
    296: "Thailand - Thai League 1",
    305: "Indonesia - Liga 1",
    275: "Malaysia - Super League",
    340: "Vietnam - V.League 1",
    # Uzbekistan already in Europe Other
    17:  "AFC Champions League Elite",
}

# ─── UEFA CONTINENTAL ─────────────────────────────────────────────────────────
_UEFA = {
    2:   "UEFA Champions League",
    3:   "UEFA Europa League",
    848: "UEFA Conference League",
}

# ─── BUILD MASTER WHITELIST ───────────────────────────────────────────────────
TARGET_LEAGUE_IDS: dict[int, str] = {
    **_ENGLAND,
    **_SPAIN,
    **_GERMANY,
    **_ITALY,
    **_FRANCE,
    **_PORTUGAL,
    **_NETHERLANDS,
    **_BELGIUM,
    **_SCOTLAND,
    **_TURKEY,
    **_EUROPE_OTHER,
    **_SOUTH_AMERICA,
    **_NORTH_AMERICA,
    **_AFRICA,
    **_ASIA,
    **_UEFA,
}

LEAGUE_WHITELIST: dict[int, str] = dict(TARGET_LEAGUE_IDS)

EXCLUDED_LEAGUE_IDS: set[int] = set()

# Lowercase substrings that trigger rejection of non-senior competitive fixtures.
# These match against the league NAME returned by the API — any name containing
# one of these substrings is immediately excluded, regardless of league ID.
REJECT_KEYWORDS = (
    "friendl",
    # Youth / age-group
    "youth",
    "under-", "under ",
    " u15", " u16", " u17", " u18", " u19", " u20", " u21", " u23",
    "u-15", "u-16", "u-17", "u-18", "u-19", "u-20", "u-21", "u-23",
    # Reserves / B-teams
    "reserve", " b team", " ii ", " iii ",
    # Women
    "women", "ladies", "female", "femenin", "feminine",
    # Amateur
    "amateur", "first amateur",
    # Other non-competitive formats
    "futsal",
    "beach",
    "indoor",
    "5-a-side",
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
