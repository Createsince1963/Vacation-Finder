"""Persistent, on-disk cache for holiday/school-holiday/subdivision data.

Replaces the purely in-memory ``holidays_by_year`` dict in ``main_window.py``
with a SQLite-backed cache that survives app restarts. Uses Python's
built-in ``sqlite3`` module - no new dependency.

Design intent (this is a CACHE, not a bulk mirror of every country):
- Rows are written lazily, only for the country/year combinations the app
  actually fetches (the user's selected country, comparison country, and
  the September-onward next-year prefetch) - never all ~98 supported
  countries at once. Eagerly warming a cache for every country would mean
  hundreds of HTTP requests against the free Nager.Date/OpenHolidays APIs
  for data nobody asked to see yet.
- ``prune_to_years()`` enforces the "current year + next year" retention
  policy: call it whenever the year may have rolled over (see
  ``MainWindow._check_year_rollover_and_prefetch``) to drop older years'
  rows instead of letting the cache grow forever.
- Each cached row carries a ``fetched_at`` timestamp; ``get_cached_*``
  treats a row older than ``max_age_days`` as a cache miss so occasional
  upstream corrections (a public holiday date change, a newly added
  subdivision) still reach the app eventually instead of being cached
  forever.

Storage/row-count math (see project feedback log for the full analysis):
with all ~98 supported countries actually visited across 2 years, holidays
land around ~3,000 rows and school holidays (which OpenHolidays breaks out
per subdivision) around ~5,000-15,000 rows - a low-single-digit-MB SQLite
file. Verified at that scale with a synthetic dataset before shipping.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from models import Holiday, SchoolHoliday, Subdivision

logger = logging.getLogger(__name__)

CACHE_DB_FILE = "holiday_cache.sqlite3"

DEFAULT_MAX_AGE_DAYS_HOLIDAYS = 14
DEFAULT_MAX_AGE_DAYS_SUBDIVISIONS = 90

_SCHEMA = """
CREATE TABLE IF NOT EXISTS holidays (
    country_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    source TEXT NOT NULL,
    date TEXT NOT NULL,
    local_name TEXT NOT NULL,
    name TEXT NOT NULL,
    fixed INTEGER NOT NULL,
    is_global INTEGER NOT NULL,
    counties_json TEXT,
    launch_year INTEGER,
    types_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_holidays_country_year_source
    ON holidays(country_code, year, source);

CREATE TABLE IF NOT EXISTS school_holidays (
    country_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    subdivision_code TEXT,
    holiday_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_school_country_year
    ON school_holidays(country_code, year, subdivision_code);

CREATE TABLE IF NOT EXISTS subdivisions (
    country_code TEXT NOT NULL,
    code TEXT NOT NULL,
    short_name TEXT NOT NULL,
    name TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (country_code, code)
);
"""


def _db_path() -> Path:
    app_data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    directory = Path(app_data_dir) if app_data_dir else Path.home() / ".vacation_finder"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / CACHE_DB_FILE


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.executescript(_SCHEMA)
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_stale(fetched_at: str, max_age_days: int | None) -> bool:
    """True if a cached row should be treated as a miss.

    ``max_age_days=None`` means "never stale" - used by the offline-fallback
    path (see api_client.py) to serve arbitrarily old cached data rather than
    nothing when the network is unavailable. A plain huge int (e.g. 10**9)
    was tried for this originally and overflows ``timedelta`` (max ~2.7
    billion days / 999999999), so ``None`` is the correct sentinel, not a
    big number.
    """
    if max_age_days is None:
        return False
    try:
        fetched = datetime.fromisoformat(fetched_at)
    except ValueError:
        return True  # unparsable timestamp -> treat as missing, refetch
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - fetched > timedelta(days=max_age_days)


# ----------------------------------------------------------------------
# Holidays
# ----------------------------------------------------------------------
def get_cached_holidays(
    country_code: str,
    year: int,
    source: str,
    max_age_days: int | None = DEFAULT_MAX_AGE_DAYS_HOLIDAYS,
) -> list[Holiday] | None:
    """Cached holidays for country/year/source, or None on a cache miss
    (never fetched, or the cached rows are older than max_age_days).

    `source` ("nager" or "openholidays") is part of the cache key: the two
    APIs can disagree slightly on names/coverage for the same country and
    year, so toggling the source in the UI must not silently keep showing
    the other source's cached data.
    """
    try:
        with closing(_connect()) as conn:
            rows = conn.execute(
                "SELECT date, local_name, name, fixed, is_global, counties_json, "
                "launch_year, types_json, fetched_at FROM holidays "
                "WHERE country_code = ? AND year = ? AND source = ?",
                (country_code, year, source),
            ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("holiday_cache read failed for %s/%s/%s: %s", country_code, year, source, exc)
        return None

    if not rows:
        return None
    if _is_stale(rows[0][8], max_age_days):
        return None

    return [
        Holiday(
            date=r[0],
            local_name=r[1],
            name=r[2],
            country_code=country_code,
            fixed=bool(r[3]),
            is_global=bool(r[4]),
            counties=json.loads(r[5]) if r[5] else None,
            launch_year=r[6],
            types=json.loads(r[7]) if r[7] else [],
        )
        for r in rows
    ]


def store_holidays(country_code: str, year: int, source: str, holidays: list[Holiday]) -> None:
    """Replace all cached rows for this country/year/source with a fresh fetch."""
    fetched_at = _now_iso()
    try:
        with closing(_connect()) as conn:
            with conn:
                conn.execute(
                    "DELETE FROM holidays WHERE country_code = ? AND year = ? AND source = ?",
                    (country_code, year, source),
                )
                conn.executemany(
                    "INSERT INTO holidays (country_code, year, source, date, local_name, name, "
                    "fixed, is_global, counties_json, launch_year, types_json, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            country_code,
                            year,
                            source,
                            h.date,
                            h.local_name,
                            h.name,
                            int(h.fixed),
                            int(h.is_global),
                            json.dumps(h.counties) if h.counties else None,
                            h.launch_year,
                            json.dumps(h.types),
                            fetched_at,
                        )
                        for h in holidays
                    ],
                )
    except sqlite3.Error as exc:
        logger.warning("holiday_cache write failed for %s/%s/%s: %s", country_code, year, source, exc)


# ----------------------------------------------------------------------
# School holidays
# ----------------------------------------------------------------------
def get_cached_school_holidays(
    country_code: str,
    year: int,
    subdivision_code: str | None,
    max_age_days: int | None = DEFAULT_MAX_AGE_DAYS_HOLIDAYS,
) -> list[SchoolHoliday] | None:
    try:
        with closing(_connect()) as conn:
            rows = conn.execute(
                "SELECT holiday_id, start_date, end_date, type, name, fetched_at "
                "FROM school_holidays WHERE country_code = ? AND year = ? "
                "AND subdivision_code IS ?",
                (country_code, year, subdivision_code),
            ).fetchall()
    except sqlite3.Error as exc:
        logger.warning(
            "holiday_cache read failed for school holidays %s/%s: %s", country_code, year, exc
        )
        return None

    if not rows:
        return None
    if _is_stale(rows[0][5], max_age_days):
        return None

    return [
        SchoolHoliday(id=r[0], start_date=r[1], end_date=r[2], type=r[3], name=r[4])
        for r in rows
    ]


def store_school_holidays(
    country_code: str,
    year: int,
    subdivision_code: str | None,
    school_holidays: list[SchoolHoliday],
) -> None:
    fetched_at = _now_iso()
    try:
        with closing(_connect()) as conn:
            with conn:
                conn.execute(
                    "DELETE FROM school_holidays WHERE country_code = ? AND year = ? "
                    "AND subdivision_code IS ?",
                    (country_code, year, subdivision_code),
                )
                conn.executemany(
                    "INSERT INTO school_holidays (country_code, year, subdivision_code, "
                    "holiday_id, start_date, end_date, type, name, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            country_code,
                            year,
                            subdivision_code,
                            sh.id,
                            sh.start_date,
                            sh.end_date,
                            sh.type,
                            sh.name,
                            fetched_at,
                        )
                        for sh in school_holidays
                    ],
                )
    except sqlite3.Error as exc:
        logger.warning(
            "holiday_cache write failed for school holidays %s/%s: %s", country_code, year, exc
        )


# ----------------------------------------------------------------------
# Subdivisions (not year-scoped - states/regions essentially never change)
# ----------------------------------------------------------------------
def get_cached_subdivisions(
    country_code: str, max_age_days: int | None = DEFAULT_MAX_AGE_DAYS_SUBDIVISIONS
) -> list[Subdivision] | None:
    try:
        with closing(_connect()) as conn:
            rows = conn.execute(
                "SELECT code, short_name, name, fetched_at FROM subdivisions "
                "WHERE country_code = ?",
                (country_code,),
            ).fetchall()
    except sqlite3.Error as exc:
        logger.warning("holiday_cache read failed for subdivisions %s: %s", country_code, exc)
        return None

    if not rows:
        return None
    if _is_stale(rows[0][3], max_age_days):
        return None

    return [Subdivision(code=r[0], short_name=r[1], name=r[2]) for r in rows]


def store_subdivisions(country_code: str, subdivisions: list[Subdivision]) -> None:
    fetched_at = _now_iso()
    try:
        with closing(_connect()) as conn:
            with conn:
                conn.execute(
                    "DELETE FROM subdivisions WHERE country_code = ?", (country_code,)
                )
                conn.executemany(
                    "INSERT INTO subdivisions (country_code, code, short_name, name, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (country_code, s.code, s.short_name, s.name, fetched_at)
                        for s in subdivisions
                    ],
                )
    except sqlite3.Error as exc:
        logger.warning("holiday_cache write failed for subdivisions %s: %s", country_code, exc)


# ----------------------------------------------------------------------
# Retention
# ----------------------------------------------------------------------
def prune_to_years(keep_years: set[int]) -> None:
    """Delete cached holiday/school-holiday rows for any year not in
    `keep_years` (subdivisions are not year-scoped and are left alone).
    Call this whenever the "current year" may have advanced, so the cache
    stays bounded to "current year + next year" instead of accumulating
    every year the app has ever displayed."""
    if not keep_years:
        return
    placeholders = ",".join("?" for _ in keep_years)
    try:
        with closing(_connect()) as conn:
            with conn:
                conn.execute(
                    f"DELETE FROM holidays WHERE year NOT IN ({placeholders})",
                    tuple(keep_years),
                )
                conn.execute(
                    f"DELETE FROM school_holidays WHERE year NOT IN ({placeholders})",
                    tuple(keep_years),
                )
    except sqlite3.Error as exc:
        logger.warning("holiday_cache prune failed: %s", exc)


def get_cache_stats() -> dict[str, int]:
    """Row counts and on-disk size, for diagnostics/testing."""
    try:
        with closing(_connect()) as conn:
            holidays_count = conn.execute("SELECT COUNT(*) FROM holidays").fetchone()[0]
            school_count = conn.execute("SELECT COUNT(*) FROM school_holidays").fetchone()[0]
            subdivisions_count = conn.execute("SELECT COUNT(*) FROM subdivisions").fetchone()[0]
    except sqlite3.Error as exc:
        logger.warning("holiday_cache stats failed: %s", exc)
        return {"holidays": 0, "school_holidays": 0, "subdivisions": 0, "file_bytes": 0}

    db_path = _db_path()
    file_bytes = db_path.stat().st_size if db_path.exists() else 0
    return {
        "holidays": holidays_count,
        "school_holidays": school_count,
        "subdivisions": subdivisions_count,
        "file_bytes": file_bytes,
    }
