"""Export the yearly day list to Excel (.xlsx) and iCal (.ics).

Fixes a bug found in the original web app's export functions: there, only
Holiday/Bridge Day/Weekend were distinguished, so Vacation and School
Holiday days silently fell into the "Weekend" bucket. Here all five
categories used in the UI are exported consistently.

Excel uses openpyxl (already part of the central Python distribution).
iCal is generated with a small stdlib-only writer (no third-party ``ics``
package required), since the central environment does not currently
include one.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from models import CalendarDay

WEEKDAY_NAMES_EN = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


def _day_type(day: CalendarDay) -> str:
    if day.is_holiday:
        return "Holiday"
    if day.is_vacation:
        return "Vacation"
    if day.is_bridge_day:
        return "Bridge Day"
    if day.is_school_holiday:
        return "School Holiday"
    return "Weekend"


def _day_description(day: CalendarDay) -> str:
    return (
        day.holiday_name
        or day.vacation_name
        or day.school_holiday_name
        or ("Bridge Day" if day.is_bridge_day else "Weekend")
    )


def _day_countries(day: CalendarDay) -> str:
    if day.is_holiday and day.holidays:
        return ", ".join(h.country_code for h in day.holidays)
    if day.is_bridge_day and day.bridge_day_countries:
        return ", ".join(day.bridge_day_countries)
    return "-"


def export_to_excel(
    days: list[CalendarDay],
    output_path: Path,
    primary_country: str,
    secondary_country: str | None,
    year: int,
) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Holidays"

    headers = ["Date", "Weekday", "Type", "Country", "Name", "KW"]
    ws.append(headers)

    for day in sorted(days, key=lambda d: d.date):
        ws.append(
            [
                day.date.strftime("%d.%m.%Y"),
                WEEKDAY_NAMES_EN[day.date.weekday()],
                _day_type(day),
                _day_countries(day),
                _day_description(day),
                day.week_number,
            ]
        )

    for idx, header in enumerate(headers, start=1):
        column = get_column_letter(idx)
        max_len = max(
            [len(header)] + [len(str(cell.value or "")) for cell in ws[column][1:]]
        )
        ws.column_dimensions[column].width = max_len + 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def _ics_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold_line(line: str) -> str:
    """RFC 5545 line folding at 75 octets, continuation lines start with a space."""
    if len(line.encode("utf-8")) <= 75:
        return line
    out = []
    current = line
    first = True
    while current:
        limit = 75 if first else 74
        chunk, current = current[:limit], current[limit:]
        out.append(chunk if first else " " + chunk)
        first = False
    return "\r\n".join(out)


def export_to_ical(
    days: list[CalendarDay],
    output_path: Path,
    primary_country_name: str,
) -> Path:
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Thomas Vacation Finder//PySide6//EN",
        "CALSCALE:GREGORIAN",
    ]

    for day in sorted(days, key=lambda d: d.date):
        countries = _day_countries(day)
        countries_str = countries if countries != "-" else primary_country_name
        summary = _day_description(day)
        description = f"{_day_type(day)} in {countries_str}"
        dt_value = day.date.strftime("%Y%m%d")
        dt_end = date.fromordinal(day.date.toordinal() + 1).strftime("%Y%m%d")

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid4()}@vacation-finder",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;VALUE=DATE:{dt_value}",
                f"DTEND;VALUE=DATE:{dt_end}",
                _fold_line(f"SUMMARY:{_ics_escape(summary)}"),
                _fold_line(f"DESCRIPTION:{_ics_escape(description)}"),
                f"CATEGORIES:{_day_type(day).upper().replace(' ', '')}",
                "STATUS:CONFIRMED",
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return output_path
