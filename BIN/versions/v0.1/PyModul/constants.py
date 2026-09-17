"""Static reference data: supported countries and selectable years.

Mirrors constants.ts from the original AI Studio web app (AI Google code/src/constants.ts).
"""

from __future__ import annotations

# Continent is used purely to group the country dropdowns in the UI
# (see main_window.py's _build_toolbar) - it has no effect on API calls,
# which are always keyed by ISO country code. A handful of countries are
# geographically transcontinental or debatable (Russia, Turkey, Georgia,
# Cyprus) - classified here by majority landmass / the grouping most
# users would look for them under, not as a geopolitical statement.
COUNTRIES: list[dict[str, str]] = [
    {"code": "AD", "name": "Andorra", "continent": "Europe"},
    {"code": "AL", "name": "Albania", "continent": "Europe"},
    {"code": "AR", "name": "Argentina", "continent": "South America"},
    {"code": "AT", "name": "Austria", "continent": "Europe"},
    {"code": "AU", "name": "Australia", "continent": "Oceania"},
    {"code": "AX", "name": "Aland Islands", "continent": "Europe"},
    {"code": "BA", "name": "Bosnia and Herzegovina", "continent": "Europe"},
    {"code": "BE", "name": "Belgium", "continent": "Europe"},
    {"code": "BG", "name": "Bulgaria", "continent": "Europe"},
    {"code": "BO", "name": "Bolivia", "continent": "South America"},
    {"code": "BR", "name": "Brazil", "continent": "South America"},
    {"code": "BY", "name": "Belarus", "continent": "Europe"},
    {"code": "CA", "name": "Canada", "continent": "North America"},
    {"code": "CH", "name": "Switzerland", "continent": "Europe"},
    {"code": "CL", "name": "Chile", "continent": "South America"},
    {"code": "CN", "name": "China", "continent": "Asia"},
    {"code": "CO", "name": "Colombia", "continent": "South America"},
    {"code": "CR", "name": "Costa Rica", "continent": "North America"},
    {"code": "CY", "name": "Cyprus", "continent": "Europe"},
    {"code": "CZ", "name": "Czechia", "continent": "Europe"},
    {"code": "DE", "name": "Germany", "continent": "Europe"},
    {"code": "DK", "name": "Denmark", "continent": "Europe"},
    {"code": "DO", "name": "Dominican Republic", "continent": "North America"},
    {"code": "EC", "name": "Ecuador", "continent": "South America"},
    {"code": "EE", "name": "Estonia", "continent": "Europe"},
    {"code": "EG", "name": "Egypt", "continent": "Africa"},
    {"code": "ES", "name": "Spain", "continent": "Europe"},
    {"code": "FI", "name": "Finland", "continent": "Europe"},
    {"code": "FO", "name": "Faroe Islands", "continent": "Europe"},
    {"code": "FR", "name": "France", "continent": "Europe"},
    {"code": "GB", "name": "United Kingdom", "continent": "Europe"},
    {"code": "GE", "name": "Georgia", "continent": "Asia"},
    {"code": "GG", "name": "Guernsey", "continent": "Europe"},
    {"code": "GI", "name": "Gibraltar", "continent": "Europe"},
    {"code": "GL", "name": "Greenland", "continent": "North America"},
    {"code": "GR", "name": "Greece", "continent": "Europe"},
    {"code": "GT", "name": "Guatemala", "continent": "North America"},
    {"code": "HK", "name": "Hong Kong", "continent": "Asia"},
    {"code": "HN", "name": "Honduras", "continent": "North America"},
    {"code": "HR", "name": "Croatia", "continent": "Europe"},
    {"code": "HU", "name": "Hungary", "continent": "Europe"},
    {"code": "ID", "name": "Indonesia", "continent": "Asia"},
    {"code": "IE", "name": "Ireland", "continent": "Europe"},
    {"code": "IM", "name": "Isle of Man", "continent": "Europe"},
    {"code": "IS", "name": "Iceland", "continent": "Europe"},
    {"code": "IT", "name": "Italy", "continent": "Europe"},
    {"code": "JE", "name": "Jersey", "continent": "Europe"},
    {"code": "JP", "name": "Japan", "continent": "Asia"},
    {"code": "KR", "name": "South Korea", "continent": "Asia"},
    {"code": "LI", "name": "Liechtenstein", "continent": "Europe"},
    {"code": "LT", "name": "Lithuania", "continent": "Europe"},
    {"code": "LU", "name": "Luxembourg", "continent": "Europe"},
    {"code": "LV", "name": "Latvia", "continent": "Europe"},
    {"code": "MA", "name": "Morocco", "continent": "Africa"},
    {"code": "MC", "name": "Monaco", "continent": "Europe"},
    {"code": "MD", "name": "Moldova", "continent": "Europe"},
    {"code": "ME", "name": "Montenegro", "continent": "Europe"},
    {"code": "MG", "name": "Madagascar", "continent": "Africa"},
    {"code": "MK", "name": "North Macedonia", "continent": "Europe"},
    {"code": "MN", "name": "Mongolia", "continent": "Asia"},
    {"code": "MT", "name": "Malta", "continent": "Europe"},
    {"code": "MX", "name": "Mexico", "continent": "North America"},
    {"code": "MY", "name": "Malaysia", "continent": "Asia"},
    {"code": "MZ", "name": "Mozambique", "continent": "Africa"},
    {"code": "NA", "name": "Namibia", "continent": "Africa"},
    {"code": "NI", "name": "Nicaragua", "continent": "North America"},
    {"code": "NL", "name": "Netherlands", "continent": "Europe"},
    {"code": "NO", "name": "Norway", "continent": "Europe"},
    {"code": "NZ", "name": "New Zealand", "continent": "Oceania"},
    {"code": "PA", "name": "Panama", "continent": "North America"},
    {"code": "PE", "name": "Peru", "continent": "South America"},
    {"code": "PK", "name": "Pakistan", "continent": "Asia"},
    {"code": "PL", "name": "Poland", "continent": "Europe"},
    {"code": "PR", "name": "Puerto Rico", "continent": "North America"},
    {"code": "PT", "name": "Portugal", "continent": "Europe"},
    {"code": "PY", "name": "Paraguay", "continent": "South America"},
    {"code": "RO", "name": "Romania", "continent": "Europe"},
    {"code": "RS", "name": "Serbia", "continent": "Europe"},
    {"code": "RU", "name": "Russia", "continent": "Europe"},
    {"code": "SE", "name": "Sweden", "continent": "Europe"},
    {"code": "SG", "name": "Singapore", "continent": "Asia"},
    {"code": "SI", "name": "Slovenia", "continent": "Europe"},
    {"code": "SJ", "name": "Svalbard and Jan Mayen", "continent": "Europe"},
    {"code": "SK", "name": "Slovakia", "continent": "Europe"},
    {"code": "SM", "name": "San Marino", "continent": "Europe"},
    {"code": "SR", "name": "Suriname", "continent": "South America"},
    {"code": "SV", "name": "El Salvador", "continent": "North America"},
    {"code": "TN", "name": "Tunisia", "continent": "Africa"},
    {"code": "TR", "name": "Turkey", "continent": "Asia"},
    {"code": "UA", "name": "Ukraine", "continent": "Europe"},
    {"code": "US", "name": "United States", "continent": "North America"},
    {"code": "UY", "name": "Uruguay", "continent": "South America"},
    {"code": "VA", "name": "Vatican City", "continent": "Europe"},
    {"code": "VE", "name": "Venezuela", "continent": "South America"},
    {"code": "VN", "name": "Vietnam", "continent": "Asia"},
    {"code": "ZA", "name": "South Africa", "continent": "Africa"},
    {"code": "ZW", "name": "Zimbabwe", "continent": "Africa"},
]

COUNTRY_NAME_BY_CODE: dict[str, str] = {c["code"]: c["name"] for c in COUNTRIES}
COUNTRY_CONTINENT_BY_CODE: dict[str, str] = {c["code"]: c["continent"] for c in COUNTRIES}

# Display order for continent groups in the UI (roughly most-to-least
# relevant for a Europe-based user, then alphabetical-ish for the rest).
CONTINENT_ORDER: list[str] = [
    "Europe",
    "North America",
    "South America",
    "Asia",
    "Africa",
    "Oceania",
]


def countries_by_continent() -> list[tuple[str, list[dict[str, str]]]]:
    """COUNTRIES grouped by continent, in CONTINENT_ORDER, each group's
    countries sorted alphabetically by name. Used to build the grouped
    country dropdowns (see main_window.py's _build_toolbar)."""
    groups: dict[str, list[dict[str, str]]] = {continent: [] for continent in CONTINENT_ORDER}
    for country in COUNTRIES:
        groups[country["continent"]].append(country)
    return [
        (continent, sorted(groups[continent], key=lambda c: c["name"]))
        for continent in CONTINENT_ORDER
        if groups[continent]
    ]


# Countries whose current-year holiday data is proactively cached at
# startup (best-effort, one request each - see MainWindow's
# _prefetch_offline_default_countries), so the app still has usable data
# for these when opened without a network connection, even before the
# user has ever manually selected them. Chosen as a DACH-centric core
# (Thomas's most likely home/work markets) plus the largest neighbouring
# European economies and the US/UK - a reasonable default, not a fixed
# requirement; edit this list to change which 8 are pre-warmed.
OFFLINE_DEFAULT_COUNTRIES: list[str] = ["DE", "AT", "CH", "FR", "IT", "ES", "GB", "US"]

YEARS: list[int] = list(range(2020, 2031))

APP_TITLE = "Thomas Vacation Finder (for Exyte......)"

NAGER_BASE_URL = "https://date.nager.at/api/v3"
OPENHOLIDAYS_BASE_URL = "https://openholidaysapi.org"

VACATIONS_STORE_FILE = "vacations.json"
