"""Annual vacation-day entitlement: base days, overtime-to-bonus-days
conversion, and carryover of unused days into the next year.

This is new functionality (the original AI Studio app had no concept of
an entitlement/budget at all - it just let you add vacations with no
limit). Settings are stored per calendar year, keyed by the four-digit
year, so a user's base entitlement or overtime hours can differ from one
year to the next (e.g. a raise in contractual vacation days).

Storage mirrors storage.py's approach: a small JSON file in the user's
app-data directory, tolerant of a missing/corrupt file (never crashes -
falls back to sensible defaults).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths

logger = logging.getLogger(__name__)

ENTITLEMENT_STORE_FILE = "entitlement.json"

DEFAULT_BASE_DAYS = 30.0
DEFAULT_HOURS_PER_DAY = 8.0
# How many years of unused days may be carried forward before being
# forfeited. Many real-world policies cap this (e.g. "use by March 31");
# we cap it at 1 year of carryover being visible/usable, which is the
# common default. This is a soft default, not a hard limit - carryover
# is still computed and shown even beyond this, just flagged.
MAX_USEFUL_CARRYOVER_YEARS = 1


@dataclass
class YearEntitlement:
    """Settings the user controls for one calendar year."""

    base_days: float = DEFAULT_BASE_DAYS
    overtime_hours: float = 0.0
    hours_per_day: float = DEFAULT_HOURS_PER_DAY
    # If set, overrides the automatically computed carryover-from-previous-
    # year value (e.g. because the user's employer capped or manually
    # adjusted it). None = use the computed value.
    carryover_override: float | None = None

    @property
    def overtime_bonus_days(self) -> float:
        """Extra flex/bridge days earned by banked overtime hours."""
        if self.hours_per_day <= 0:
            return 0.0
        return self.overtime_hours / self.hours_per_day


def _store_path() -> Path:
    app_data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    directory = Path(app_data_dir) if app_data_dir else Path.home() / ".vacation_finder"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / ENTITLEMENT_STORE_FILE


def load_entitlement_settings() -> dict[int, YearEntitlement]:
    """Load all per-year settings. Missing/corrupt file -> empty dict."""
    path = _store_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read entitlement store (%s), starting empty: %s", path, exc)
        return {}

    settings: dict[int, YearEntitlement] = {}
    for key, item in (raw if isinstance(raw, dict) else {}).items():
        try:
            year = int(key)
            settings[year] = YearEntitlement(
                base_days=float(item.get("baseDays", DEFAULT_BASE_DAYS)),
                overtime_hours=float(item.get("overtimeHours", 0.0)),
                hours_per_day=float(item.get("hoursPerDay", DEFAULT_HOURS_PER_DAY)),
                carryover_override=(
                    float(item["carryoverOverride"])
                    if item.get("carryoverOverride") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed entitlement entry for %r: %r", key, item)
    return settings


def save_entitlement_settings(settings: dict[int, YearEntitlement]) -> None:
    path = _store_path()
    payload = {
        str(year): {
            "baseDays": s.base_days,
            "overtimeHours": s.overtime_hours,
            "hoursPerDay": s.hours_per_day,
            "carryoverOverride": s.carryover_override,
        }
        for year, s in settings.items()
    }
    try:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.error("Could not save entitlement store (%s): %s", path, exc)


def get_year_entitlement(
    settings: dict[int, YearEntitlement], year: int
) -> YearEntitlement:
    """Settings for a year, or fresh defaults if the user hasn't configured it yet."""
    return settings.get(year, YearEntitlement())


@dataclass
class YearBudget:
    """Computed vacation-day budget for one calendar year."""

    base_days: float
    overtime_bonus_days: float
    carryover_from_previous_year: float
    used_days: float

    @property
    def total_available(self) -> float:
        return self.base_days + self.overtime_bonus_days + self.carryover_from_previous_year

    @property
    def remaining(self) -> float:
        return self.total_available - self.used_days


def compute_carryover(previous_year_budget: YearBudget | None) -> float:
    """Unused days from the previous year, clamped to zero (never negative -
    over-booking a year's budget must not create a debt on the next year)."""
    if previous_year_budget is None:
        return 0.0
    return max(0.0, previous_year_budget.remaining)


def compute_year_budget(
    settings: dict[int, YearEntitlement],
    year: int,
    used_days: float,
    previous_year_budget: YearBudget | None = None,
) -> YearBudget:
    """Build the full budget for `year`.

    Carryover is either the user's manual override for that year, or the
    automatically computed leftover from `previous_year_budget` (pass the
    already-computed budget for `year - 1` so multi-year chains work
    correctly without recursion here).
    """
    entitlement = get_year_entitlement(settings, year)
    carryover = (
        entitlement.carryover_override
        if entitlement.carryover_override is not None
        else compute_carryover(previous_year_budget)
    )
    return YearBudget(
        base_days=entitlement.base_days,
        overtime_bonus_days=entitlement.overtime_bonus_days,
        carryover_from_previous_year=carryover,
        used_days=used_days,
    )
