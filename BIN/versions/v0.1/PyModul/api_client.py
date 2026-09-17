"""HTTP clients for the two free, no-API-key holiday data sources.

- Nager.Date (https://date.nager.at) - public holidays only.
- OpenHolidays API (https://openholidaysapi.org) - public holidays, school
  holidays and subdivisions (states/regions).

Both are open, unauthenticated REST APIs. No API key is required or used
anywhere in this module.
"""

from __future__ import annotations

import logging

import requests

from constants import NAGER_BASE_URL, OPENHOLIDAYS_BASE_URL
from models import Holiday, SchoolHoliday, Subdivision

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15


def fetch_subdivisions(country_code: str) -> list[Subdivision]:
    """Return the states/regions of a country (e.g. German Bundeslaender)."""
    url = f"{OPENHOLIDAYS_BASE_URL}/Subdivisions"
    try:
        resp = requests.get(
            url,
            params={"countryIsoCode": country_code},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as exc:
        logger.warning("fetch_subdivisions(%s) failed: %s", country_code, exc)
        return []

    subdivisions: list[Subdivision] = []
    for item in raw:
        names = item.get("name") or []
        text = names[0]["text"] if names else item.get("code", "")
        subdivisions.append(
            Subdivision(
                code=item.get("code", ""),
                short_name=item.get("shortName", item.get("code", "")),
                name=text,
            )
        )
    return subdivisions


def fetch_school_holidays(
    country_code: str,
    year: int,
    subdivision_code: str | None = None,
) -> list[SchoolHoliday]:
    """Return school holidays for a country/year, optionally scoped to a subdivision."""
    url = f"{OPENHOLIDAYS_BASE_URL}/SchoolHolidays"
    params = {
        "countryIsoCode": country_code,
        "languageIsoCode": "EN",
        "validFrom": f"{year}-01-01",
        "validTo": f"{year}-12-31",
    }
    if subdivision_code:
        params["subdivisionCode"] = subdivision_code

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as exc:
        logger.warning("fetch_school_holidays(%s, %s) failed: %s", country_code, year, exc)
        return []

    result: list[SchoolHoliday] = []
    for item in raw:
        names = item.get("name") or []
        text = names[0]["text"] if names else ""
        result.append(
            SchoolHoliday(
                id=item.get("id", ""),
                start_date=item.get("startDate", ""),
                end_date=item.get("endDate", ""),
                type=item.get("type", ""),
                name=text,
            )
        )
    return result


def fetch_country_holidays(
    country_code: str,
    year: int,
    source: str = "nager",
    subdivision_code: str | None = None,
) -> list[Holiday]:
    """Return public holidays for a country/year from the selected source.

    Note: neither Nager.Date nor the OpenHolidays public-holiday endpoint
    filter by subdivision server-side - both always return every holiday
    for the whole country in one response, each carrying its own scope
    (nationwide, or a list of subdivision codes it applies to, e.g.
    "DE-BW"). ``subdivision_code`` is accepted here for symmetry with
    ``fetch_school_holidays`` but currently unused - callers should filter
    the returned list themselves with :func:`holiday_applies_to_subdivision`
    once the desired subdivision is known (see ``MainWindow._visible_holidays``).
    """
    if source == "nager":
        return _fetch_nager_holidays(country_code, year)
    return _fetch_openholidays_holidays(country_code, year)


def _fetch_nager_holidays(country_code: str, year: int) -> list[Holiday]:
    url = f"{NAGER_BASE_URL}/PublicHolidays/{year}/{country_code}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as exc:
        logger.warning("Nager.Date fetch failed for %s/%s: %s", year, country_code, exc)
        return []

    holidays: list[Holiday] = []
    for item in raw:
        holidays.append(
            Holiday(
                date=item.get("date", ""),
                local_name=item.get("localName", item.get("name", "")),
                name=item.get("name", ""),
                country_code=item.get("countryCode", country_code),
                fixed=item.get("fixed", False),
                is_global=item.get("global", True),
                counties=item.get("counties"),
                launch_year=item.get("launchYear"),
                types=item.get("types", []),
            )
        )
    return holidays


def _fetch_openholidays_holidays(country_code: str, year: int) -> list[Holiday]:
    url = f"{OPENHOLIDAYS_BASE_URL}/PublicHolidays"
    params = {
        "countryIsoCode": country_code,
        "languageIsoCode": "EN",
        "validFrom": f"{year}-01-01",
        "validTo": f"{year}-12-31",
    }
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        raw = resp.json()
    except requests.RequestException as exc:
        logger.warning("OpenHolidays fetch failed for %s/%s: %s", year, country_code, exc)
        return []

    holidays: list[Holiday] = []
    for item in raw:
        names = item.get("name") or []
        en_name = next((n["text"] for n in names if n.get("language") == "EN"), None)
        local_name = names[0]["text"] if names else ""
        subdivisions = item.get("subdivisions") or []
        holidays.append(
            Holiday(
                date=item.get("startDate", ""),
                local_name=local_name,
                name=en_name or local_name,
                country_code=country_code,
                fixed=True,
                is_global=item.get("nationwide", True),
                # OpenHolidays returns per-holiday subdivision scope even
                # though the query itself cannot be filtered by
                # subdivisionCode server-side (see holiday_applies_to_subdivision).
                counties=[s["code"] for s in subdivisions] or None,
                launch_year=None,
                types=[item.get("type", "")],
            )
        )
    return holidays


def holiday_applies_to_subdivision(holiday: Holiday, subdivision_code: str | None) -> bool:
    """True if a holiday should be shown when this subdivision is selected.

    Both Nager.Date and OpenHolidays return every holiday for the whole
    country in one call - state/region scoping (e.g. "Fronleichnam" only in
    a few German Bundeslaender, or a canton-specific Swiss holiday) has to
    be applied client-side using the ``counties``/``subdivisions`` field
    each holiday already carries. With no subdivision selected, or a
    nationwide holiday, it always applies.
    """
    if not subdivision_code:
        return True
    if holiday.is_global or not holiday.counties:
        return True
    return subdivision_code in holiday.counties
