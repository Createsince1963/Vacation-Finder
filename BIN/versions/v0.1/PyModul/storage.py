"""Local persistence for planned vacations.

Replaces the original app's ``localStorage`` usage with a small JSON file
in the user's app-data directory. Unlike the original
(``JSON.parse(localStorage.getItem(...))`` with no error handling), a
corrupt or missing file here never crashes the app - see the code review
finding this addresses.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from constants import VACATIONS_STORE_FILE
from models import Vacation

logger = logging.getLogger(__name__)


def _store_path() -> Path:
    app_data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    directory = Path(app_data_dir) if app_data_dir else Path.home() / ".vacation_finder"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / VACATIONS_STORE_FILE


def load_vacations() -> list[Vacation]:
    path = _store_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read vacations store (%s), starting empty: %s", path, exc)
        return []

    vacations: list[Vacation] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            vacations.append(
                Vacation(
                    id=item["id"],
                    start_date=item["startDate"],
                    end_date=item["endDate"],
                    name=item["name"],
                    # Missing key = data written before half-day support existed.
                    half_day=bool(item.get("halfDay", False)),
                )
            )
        except (KeyError, TypeError):
            logger.warning("Skipping malformed vacation entry: %r", item)
    return vacations


def save_vacations(vacations: list[Vacation]) -> None:
    path = _store_path()
    payload = [
        {
            "id": v.id,
            "startDate": v.start_date,
            "endDate": v.end_date,
            "name": v.name,
            "halfDay": v.half_day,
        }
        for v in vacations
    ]
    try:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.error("Could not save vacations store (%s): %s", path, exc)


def new_vacation_id() -> str:
    return uuid.uuid4().hex[:12]
