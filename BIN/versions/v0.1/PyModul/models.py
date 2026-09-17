"""Data models shared across the app.

Mirrors types.ts from the original AI Studio web app (AI Google code/src/types.ts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Holiday:
    date: str  # ISO format YYYY-MM-DD
    local_name: str
    name: str
    country_code: str
    fixed: bool = True
    is_global: bool = True
    counties: list[str] | None = None
    launch_year: int | None = None
    types: list[str] = field(default_factory=list)


@dataclass
class SchoolHoliday:
    id: str
    start_date: str
    end_date: str
    type: str
    name: str


@dataclass
class Subdivision:
    code: str
    short_name: str
    name: str


@dataclass
class Vacation:
    id: str
    start_date: str
    end_date: str
    name: str
    # Half-day vacation: only meaningful when start_date == end_date.
    # A multi-day range is always counted in full days (the original app,
    # like most real-world policies, only allows a half day for single-day
    # entries - e.g. "leave at noon" or "arrive at noon").
    half_day: bool = False


@dataclass
class CalendarDay:
    date: date
    is_holiday: bool = False
    is_bridge_day: bool = False
    is_vacation: bool = False
    is_school_holiday: bool = False
    is_weekend: bool = False
    week_number: int = 0
    holiday_name: str | None = None
    vacation_name: str | None = None
    school_holiday_name: str | None = None
    holidays: list[Holiday] = field(default_factory=list)
    bridge_day_countries: list[str] = field(default_factory=list)
