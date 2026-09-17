"""Pure calendar/date logic: week numbers, bridge-day detection, day generation.

Mirrors the helper functions inside AI Google code/src/App.tsx
(formatDate, getWeekNumber, generateMonthDays), translated to Python.
Kept dependency-free (only stdlib datetime) so it can be unit tested
without a Qt event loop.

Bridge-day detection (``compute_bridge_days``) is a deliberate improvement
over the original app's per-day heuristic (``AI Google code/src/App.tsx``,
``isBridgeDay``), which only looked at each day's immediate neighbour and
therefore over-flagged days that do not actually connect to a weekend or
another holiday (e.g. a Wednesday next to a Thursday holiday, with no
weekend or holiday on its other side). See the module docstring of
``compute_bridge_days`` for the corrected algorithm.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from models import CalendarDay, Holiday, SchoolHoliday, Vacation

DEFAULT_MAX_BRIDGE_GAP = 2


def format_date(d: date) -> str:
    """ISO YYYY-MM-DD, matching the original app's local-date formatting."""
    return d.isoformat()


def get_week_number(d: date) -> int:
    """ISO-8601 week number (same definition as the original app's getWeekNumber)."""
    return d.isocalendar()[1]


def compute_bridge_days(
    year: int,
    holiday_dates: set[str],
    max_gap: int = DEFAULT_MAX_BRIDGE_GAP,
) -> set[str]:
    """Return the ISO dates of genuine bridge days ("Bruecken-"/"Gleittage") for a year.

    A bridge day is a short run of consecutive working weekdays (length
    1..``max_gap``) that is flanked on BOTH sides by a non-working day
    (weekend or public holiday). Only days meeting that condition are
    returned - a single day next to a holiday that does *not* also lead
    into a weekend or another holiday is correctly excluded, unlike the
    original app's per-day adjacency check.

    ``max_gap`` is user-tunable in the UI (default 2, i.e. "up to 2 days"),
    so a stricter or more generous definition of "worth taking off" can be
    chosen instead of hard-coding one behaviour.
    """
    if max_gap < 1:
        return set()

    # Pad a few days into the neighbouring years so gaps spanning
    # Dec 31 / Jan 1 are still detected correctly, then filter back down
    # to the requested year before returning.
    padding = timedelta(days=max_gap + 1)
    start = date(year, 1, 1) - padding
    end = date(year, 12, 31) + padding

    def is_non_working(d: date) -> bool:
        return d.weekday() >= 5 or format_date(d) in holiday_dates

    bridge_days: set[str] = set()
    current = start
    while current <= end:
        if is_non_working(current):
            current += timedelta(days=1)
            continue

        gap_start = current
        gap_end = current
        while gap_end + timedelta(days=1) <= end and not is_non_working(gap_end + timedelta(days=1)):
            gap_end += timedelta(days=1)

        gap_length = (gap_end - gap_start).days + 1
        day_before = gap_start - timedelta(days=1)
        day_after = gap_end + timedelta(days=1)

        if gap_length <= max_gap and is_non_working(day_before) and is_non_working(day_after):
            d = gap_start
            while d <= gap_end:
                bridge_days.add(format_date(d))
                d += timedelta(days=1)

        current = gap_end + timedelta(days=1)

    return {ds for ds in bridge_days if ds.startswith(f"{year}-")}


def generate_month_days(
    year: int,
    month: int,  # 1-12
    holidays: list[Holiday],
    bridge_dates_primary: set[str],
    bridge_dates_secondary: set[str] | None,
    primary_country: str,
    secondary_country: str | None,
    vacations: list[Vacation],
    school_holidays: list[SchoolHoliday],
) -> list[CalendarDay]:
    """Build one CalendarDay per day of the given month, with all flags set.

    ``bridge_dates_primary``/``bridge_dates_secondary`` must be precomputed
    with :func:`compute_bridge_days` for the *whole year* (not just this
    month), since a valid bridge-day gap can span a month boundary.
    """
    days_in_month = monthrange(year, month)[1]
    holidays_by_date: dict[str, list[Holiday]] = {}
    for h in holidays:
        holidays_by_date.setdefault(h.date, []).append(h)

    result: list[CalendarDay] = []
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        date_str = format_date(d)
        day_holidays = holidays_by_date.get(date_str, [])

        bridge_countries: list[str] = []
        if date_str in bridge_dates_primary:
            bridge_countries.append(primary_country)
        if secondary_country and bridge_dates_secondary and date_str in bridge_dates_secondary:
            bridge_countries.append(secondary_country)

        vacation = next(
            (v for v in vacations if v.start_date <= date_str <= v.end_date), None
        )
        school_holiday = next(
            (sh for sh in school_holidays if sh.start_date <= date_str <= sh.end_date),
            None,
        )

        result.append(
            CalendarDay(
                date=d,
                is_holiday=len(day_holidays) > 0,
                holiday_name=", ".join(h.name for h in day_holidays) or None,
                holidays=day_holidays,
                is_bridge_day=len(bridge_countries) > 0,
                bridge_day_countries=bridge_countries,
                is_weekend=d.weekday() >= 5,
                week_number=get_week_number(d),
                is_vacation=vacation is not None,
                vacation_name=vacation.name if vacation else None,
                is_school_holiday=school_holiday is not None,
                school_holiday_name=school_holiday.name if school_holiday else None,
            )
        )
    return result


def calculate_working_days(
    start_str: str,
    end_str: str,
    holiday_dates: set[str],
) -> int:
    """Count weekdays that are neither a weekend day nor a public holiday."""
    if not start_str or not end_str:
        return 0
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    if end < start:
        return 0

    count = 0
    current = start
    one_day = timedelta(days=1)
    while current <= end:
        if current.weekday() < 5 and format_date(current) not in holiday_dates:
            count += 1
        current += one_day
    return count


def vacation_day_count(
    start_str: str,
    end_str: str,
    half_day: bool,
    holiday_dates: set[str],
) -> float:
    """Like ``calculate_working_days``, but a half-day single-day vacation
    on a working day counts as 0.5 instead of 1. A half-day flag on a
    range longer than one day, or on a day that is a weekend/holiday
    anyway (0 working days), has no effect.
    """
    full_days = calculate_working_days(start_str, end_str, holiday_dates)
    if half_day and start_str == end_str and full_days == 1:
        return 0.5
    return float(full_days)


def working_days_in_year(
    start_str: str,
    end_str: str,
    half_day: bool,
    holiday_dates: set[str],
    year: int,
) -> float:
    """Portion of a (possibly year-spanning) vacation that falls in ``year``.

    Used for annual-entitlement bookkeeping: a vacation that crosses a
    year boundary (e.g. 2026-12-29 to 2027-01-04) must only count against
    each year's own budget for the days actually in that year.
    """
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    clipped_start = max(start, year_start)
    clipped_end = min(end, year_end)
    if clipped_start > clipped_end:
        return 0.0
    clipped_half_day = half_day and clipped_start == start and clipped_end == end
    return vacation_day_count(
        format_date(clipped_start), format_date(clipped_end), clipped_half_day, holiday_dates
    )
