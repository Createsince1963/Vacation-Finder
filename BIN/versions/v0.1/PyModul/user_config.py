"""Small local user-configuration store - currently just the UI language.

Kept deliberately minimal ("kleine user konfig"): a single small JSON file
in the app-data directory, same shape/robustness as storage.py's
vacations.json and entitlement.py's entitlement.json (missing/corrupt file
never crashes the app, just falls back to defaults). This is the natural
place to add further small user-level settings later without needing a
bigger settings framework.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

USER_CONFIG_STORE_FILE = "user_config.json"
_SUPPORTED_LANGUAGE_CODES = {code for code, _ in SUPPORTED_LANGUAGES}


@dataclass
class UserConfig:
    language: str = DEFAULT_LANGUAGE


def _store_path() -> Path:
    app_data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    directory = Path(app_data_dir) if app_data_dir else Path.home() / ".vacation_finder"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / USER_CONFIG_STORE_FILE


def load_user_config() -> UserConfig:
    path = _store_path()
    if not path.exists():
        return UserConfig()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read user config (%s), using defaults: %s", path, exc)
        return UserConfig()

    language = raw.get("language", DEFAULT_LANGUAGE) if isinstance(raw, dict) else DEFAULT_LANGUAGE
    if language not in _SUPPORTED_LANGUAGE_CODES:
        language = DEFAULT_LANGUAGE
    return UserConfig(language=language)


def save_user_config(config: UserConfig) -> None:
    path = _store_path()
    try:
        path.write_text(
            json.dumps({"language": config.language}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Could not save user config (%s): %s", path, exc)
