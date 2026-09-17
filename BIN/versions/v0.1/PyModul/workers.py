"""Background network fetch, kept off the Qt UI thread.

Uses a QThread + QObject worker pair (the standard PySide6 pattern) instead
of calling ``requests`` directly from the UI thread, which would freeze the
window while waiting on the network - a problem the original React app did
not have to think about (the browser's fetch() is async by default).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

import api_client
from models import Holiday, SchoolHoliday, Subdivision


class HolidayFetchWorker(QObject):
    finished = Signal(list, list, list)  # holidays, school_holidays, subdivisions
    failed = Signal(str)

    def __init__(
        self,
        primary_country: str,
        secondary_country: str | None,
        year: int,
        source: str,
        subdivision_code: str | None,
        fetch_subdivisions: bool,
    ) -> None:
        super().__init__()
        self.primary_country = primary_country
        self.secondary_country = secondary_country
        self.year = year
        self.source = source
        self.subdivision_code = subdivision_code
        self.fetch_subdivisions_flag = fetch_subdivisions

    def run(self) -> None:
        try:
            holidays: list[Holiday] = list(
                api_client.fetch_country_holidays(self.primary_country, self.year, self.source)
            )
            if self.secondary_country:
                holidays += api_client.fetch_country_holidays(
                    self.secondary_country, self.year, self.source
                )

            school_holidays: list[SchoolHoliday] = api_client.fetch_school_holidays(
                self.primary_country, self.year, self.subdivision_code
            )

            subdivisions: list[Subdivision] = []
            if self.fetch_subdivisions_flag:
                subdivisions = api_client.fetch_subdivisions(self.primary_country)

            self.finished.emit(holidays, school_holidays, subdivisions)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))


def start_holiday_fetch(
    parent: QObject,
    primary_country: str,
    secondary_country: str | None,
    year: int,
    source: str,
    subdivision_code: str | None,
    fetch_subdivisions: bool,
    on_finished,
    on_failed,
) -> tuple[QThread, HolidayFetchWorker]:
    """Spin up a worker thread and wire its signals. Returns (thread, worker) -
    the caller must keep both alive (e.g. as attributes on itself) until
    ``finished``/``failed`` fires, otherwise Qt garbage-collects them mid-flight.
    """
    thread = QThread(parent)
    worker = HolidayFetchWorker(
        primary_country, secondary_country, year, source, subdivision_code, fetch_subdivisions
    )
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker
