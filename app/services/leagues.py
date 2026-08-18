"""
PHASE 5 — Strict Target League scanning rules.

Exact 63 requested leagues and major tournaments:
 1. Brazil - Copa Paulista (480)
 2. Argentina - Copa Argentina (130)
 3. International Clubs - CONMEBOL Libertadores (13)
 4. Brazil - Brasileiro Serie B (72)
 5. Republic of Korea - Korea Cup (294)
 6. Tanzania - Premier League (393)
 7. China - Chinese Super League (169)
 8. Russia - Russian Cup (237)
 9. Greece - Greece Cup (210)
10. Uzbekistan - Superliga (365)
11. Romania - Romania Cup (546)
12. Slovakia - Slovensky Pohar (334)
13. Czechia - Czech Cup (347)
14. Belarus - Vysshaya Liga (244)
15. South Africa - Premiership (288)
16. England - EFL Trophy (46)
17. Argentina - Primera Nacional (129)
18. England Amateur - National League South (43)
19. Colombia - Torneo DIMAYOR (240)
20. Bolivia - Copa Bolivia (913)
21. Paraguay - Copa Paraguay (786)
22. Spain - LaLiga (140)
23. USA - MLS Next Pro (909)
24. International Clubs - UEFA Europa League (3)
25. Saudi Arabia - Saudi Pro League (307)
26. Japan - J1 League (98)
27. Latvia - Virsliga (261)
28. Germany - DFB Pokal (81)
29. Denmark - 1. Division (120)
30. Estonia - Premium Liiga (327)
31. Finland - Veikkausliiga (247)
32. Poland - 1. Liga (107)
33. Czechia - FNL (346)
34. Finland - Ykkosliiga (248)
35. Austria - 2. Liga (219)
36. Switzerland - Challenge League (208)
37. France - Ligue 2 (62)
38. Netherlands - Eerste Divisie (89)
39. Wales - Cymru Premier (113)
40. Ireland - Premier Division (357)
41. Italy - Serie C, Group A (138)
42. Italy - Serie C, Group C (944)
43. Mexico - Liga MX (262)
44. Romania - Liga 2 (284)
45. Japan - J2 League (99)
46. Portugal - Liga Portugal 2 (95)
47. Republic of Korea - K-League 1 (292)
48. England - Championship (40)
49. England - League Two (42)
50. England - National League (44)
51. Sweden - Allsvenskan (119)
52. Poland - Ekstraklasa (106)
53. Scotland - Premiership (179)
54. Scotland - League 1 (183)
55. Scotland - League 2 (184)
56. England - League One (41)
57. Czechia - 1. Liga (345)
58. Austria - Bundesliga (218)
59. Turkiye - Super Lig (203)
60. Bulgaria - Parva Liga (172)
61. Peru - Liga 1 (281)
62. Slovakia - Superliga (332)
63. Argentina - Primera C (131)
"""

SCAN_ALL_LEAGUES = False

# Whitelisted 63 Requested League IDs (API-Football IDs)
TARGET_LEAGUE_IDS: dict[int, str] = {
    480: "Brazil - Copa Paulista",
    130: "Argentina - Copa Argentina",
    13: "International Clubs - CONMEBOL Libertadores",
    72: "Brazil - Brasileiro Serie B",
    294: "Republic of Korea - Korea Cup",
    393: "Tanzania - Premier League",
    169: "China - Chinese Super League",
    237: "Russia - Russian Cup",
    210: "Greece - Greece Cup",
    365: "Uzbekistan - Superliga",
    546: "Romania - Romania Cup",
    334: "Slovakia - Slovensky Pohar",
    347: "Czechia - Czech Cup",
    244: "Belarus - Vysshaya Liga",
    288: "South Africa - Premiership",
    46: "England - EFL Trophy",
    129: "Argentina - Primera Nacional",
    43: "England Amateur - National League South",
    240: "Colombia - Torneo DIMAYOR",
    913: "Bolivia - Copa Bolivia",
    786: "Paraguay - Copa Paraguay",
    140: "Spain - LaLiga",
    909: "USA - MLS Next Pro",
    3: "International Clubs - UEFA Europa League",
    307: "Saudi Arabia - Saudi Pro League",
    98: "Japan - J1 League",
    261: "Latvia - Virsliga",
    81: "Germany - DFB Pokal",
    120: "Denmark - 1. Division",
    327: "Estonia - Premium Liiga",
    247: "Finland - Veikkausliiga",
    107: "Poland - 1. Liga",
    346: "Czechia - FNL",
    248: "Finland - Ykkosliiga",
    219: "Austria - 2. Liga",
    208: "Switzerland - Challenge League",
    62: "France - Ligue 2",
    89: "Netherlands - Eerste Divisie",
    113: "Wales - Cymru Premier",
    357: "Ireland - Premier Division",
    138: "Italy - Serie C, Group A",
    944: "Italy - Serie C, Group C",
    262: "Mexico - Liga MX",
    284: "Romania - Liga 2",
    99: "Japan - J2 League",
    95: "Portugal - Liga Portugal 2",
    292: "Republic of Korea - K-League 1",
    40: "England - Championship",
    42: "England - League Two",
    44: "England - National League",
    119: "Sweden - Allsvenskan",
    106: "Poland - Ekstraklasa",
    179: "Scotland - Premiership",
    183: "Scotland - League 1",
    184: "Scotland - League 2",
    41: "England - League One",
    345: "Czechia - 1. Liga",
    218: "Austria - Bundesliga",
    203: "Turkiye - Super Lig",
    172: "Bulgaria - Parva Liga",
    281: "Peru - Liga 1",
    332: "Slovakia - Superliga",
    131: "Argentina - Primera C",
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
