# APK Vacation Finder - Feedback for Admin
**Date:** 2026-09-17 17:30
**Version:** v0.1 (PyModul)

## What changed in this batch

Two explicit requests: a small user config (modeled after the compact
"one JSON settings file" approach) with an 8-language picker, and making
the toolbar search field actually filter the calendar views (a known,
previously-flagged v1 gap).

### New module: `user_config.py`
- `UserConfig` dataclass, currently just `language: str`.
- Persisted to `user_config.json` in the app-data directory - same
  minimal, crash-tolerant JSON-file pattern as `storage.py`/`entitlement.py`
  (missing/corrupt file -> falls back to English, invalid/unknown language
  code -> falls back to English).
- Deliberately small/single-purpose ("kleine user konfig") - a natural
  place to add further small user-level settings later.

### New module: `i18n.py`
- Dict-based UI translation layer (not Qt Linguist - no .ts/.qm build
  step needed, simpler for this app's modest label count).
- 8 languages picked as the most broadly useful mix of native-speaker
  reach and international business relevance: English, German, Spanish,
  French, Portuguese, Italian, Chinese (Simplified), Arabic.
- 70 translation keys per language (280 short UI strings total),
  consistency-checked (every language has every key, no holes).
- Covers: toolbar labels, view/filter buttons, export/vacation buttons,
  panel titles, all table column headers, the day-type words used in the
  List/Month views ("Holiday", "Bridge Day", etc.), the Vacation Budget
  summary line's words, and full month names (used in the Month view
  title and the Year view's per-month group boxes).
- Explicitly NOT translated (documented scope cut, not an oversight):
  native OS file-save dialog chrome, error message text, and weekday
  names (`strftime("%A")` follows the OS locale, not this app's language
  setting - translating that would need locale switching, a bigger change).

### `main_window.py` wiring
- New "Language" dropdown in the toolbar (native names: English, Deutsch,
  Español, Français, Português, Italiano, 中文, العربية), persists on
  change, and calls `_retranslate_ui()` which updates every static widget
  in place (no restart needed) and re-renders the dynamic panels so they
  pick up the new language immediately.
- Search field: previously stored the typed text but did nothing else
  (flagged as a known gap in the last feedback log). Now:
  - **List view**: non-matching days are filtered out entirely.
  - **Month/Year views**: matching days are highlighted (yellow), all
    other days are dimmed (light gray) - the grid structure stays intact
    (can't remove cells without breaking date alignment), but the search
    term's effect is clearly visible.
  - Matches against: holiday name, vacation name, school-holiday name,
    the "Bridge Day" label/country codes, and the "Weekend" label - all
    matched in the currently selected UI language.

## Testing performed
All headless (`QT_QPA_PLATFORM=offscreen`, real PySide6 6.11, network
calls mocked):
- `i18n.py`: all 8 languages have all 70 keys (no holes), spot-checked
  translations (DE/ZH/AR), unknown-key and unknown-language fallback
  behavior, month-name lookup.
- `user_config.py`: default language, save/reload round-trip, invalid
  language code falls back to English, corrupt JSON falls back to
  English (logged, not crashed).
- Full app (headless): language switch via the combo box updates labels,
  panel titles, table headers, and the budget summary line live, in
  German/Arabic/Chinese/back to English; confirmed the choice persists
  across a fresh `load_user_config()` call (simulating app restart).
- Search filtering: confirmed the List view's row count actually drops
  when a search term is entered and returns 0 rows for a nonsense term;
  confirmed the Month view (on the holiday's actual month, not just
  "today's" month) shows both a highlighted match and dimmed non-matches;
  same check repeated for the Year view's per-month grids.

## Not yet done / still open
- WSL2 status check and the actual Android APK build are still pending -
  blocked on the user running `wsl --status` / `wsl -l -v` in PowerShell.
- Weekday names, OS file-dialog chrome, and error/status message text
  beyond "Ready" are not translated (documented scope cut above).
- No live test yet against the real network APIs from the user's own
  machine (only mocked/offline testing so far in this sandbox).
