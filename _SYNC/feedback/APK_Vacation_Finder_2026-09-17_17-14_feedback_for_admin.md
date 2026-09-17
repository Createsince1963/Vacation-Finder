# APK Vacation Finder - Feedback for Admin
**Date:** 2026-09-17 17:14
**Version:** v0.1 (PyModul)

## What changed in this batch

Implemented the compound feature request: automatic year rollover, September-onward
next-year prefetch, annual vacation-day entitlement with carryover, overtime-to-bonus-days
conversion, and half-day vacations.

### New module: `entitlement.py`
- `YearEntitlement` (per-year, user-editable): base days/year, overtime hours,
  hours-per-day (for the overtime -> bonus-days conversion), optional manual
  carryover override.
- `YearBudget` (computed): base days + overtime bonus days + carryover from
  previous year, minus days used -> remaining.
- Persisted to `entitlement.json` in the app-data directory (same pattern as
  `storage.py`'s `vacations.json`), tolerant of a missing/corrupt file.
- Carryover is clamped to >= 0 (overspending one year's budget never creates
  a debt that reduces the next year's days).

### Half-day vacations (`models.py`, `calendar_logic.py`, `storage.py`, `vacation_dialog.py`)
- `Vacation.half_day: bool`, only meaningful when start_date == end_date (a
  multi-day range is always counted in full days - matches how real-world
  policies handle this).
- New `vacation_day_count()` (0.5-aware) and `working_days_in_year()` (splits
  a year-spanning vacation's day count across the two years it touches, e.g.
  a trip from 2026-12-29 to 2027-01-04 only counts the in-2026 days against
  2026's budget and the in-2027 days against 2027's).
- `VacationDialog` gained a "Half day" checkbox, enabled only when start =
  end date, live-updating the working-days preview (shows "0.5" via `:g`
  formatting).
- `storage.py` reads old vacation entries with no `halfDay` key as `False`
  (backward compatible with data saved before this change).

### Automatic year rollover + September prefetch (`main_window.py`)
- An hourly `QTimer` checks whether the real-world year has advanced; if so
  (and the user hasn't manually pinned a different year - tracked via
  `_year_follows_today`), the app switches `selected_year` and refreshes.
- From September onward, next year's holiday data is silently fetched in
  the background (`_start_prefetch_next_year`) into a new multi-year cache
  (`holidays_by_year`/`school_holidays_by_year`), so the Jan 1 rollover (or
  the user manually picking next year) doesn't have to wait on the network.
- Prefetch failures are silent by design (retried on the next hourly check)
  since it's a background warm-up, not a user-initiated action.
- `closeEvent` now also safely waits on/guards the prefetch thread (same
  `RuntimeError`-guard pattern as the existing fetch-thread fix).

### New "Vacation Budget" panel (`main_window.py`)
- Editable Base days/year, Overtime hours, Hours/day fields (persist on
  change via `_save_current_year_entitlement`).
- Summary line: `<year>: X available (base + overtime-bonus + carryover) |
  Used: Y | Remaining: Z`, turns red when remaining < 0.
- Replaces the old hardcoded "> 30 days" warning in the vacations panel,
  which is now just a simple "total planned across all vacations" figure.

### Bug found & fixed during testing: phantom carryover
While testing `_compute_budget_for_year`, found that a year with no prior
year's entitlement configured would still show a full default "30 days
carried over" - because `YearEntitlement()`'s own default base_days is 30,
even for a year the user never touched. Fixed: carryover is now only
computed if the previous year has explicit entitlement settings *or* has
recorded vacations; otherwise it's correctly 0.

## Testing performed
All of the following ran headlessly in the sandbox (network calls mocked
where needed, real PySide6 6.11 with `QT_QPA_PLATFORM=offscreen`):
- `calendar_logic.py`: half-day counting, weekend/holiday half-day edge
  cases, year-spanning split (2026/2027 boundary), half-day at exact year
  boundary.
- `storage.py`: backward-compat load of pre-half-day data, half-day
  round-trip save/load.
- `entitlement.py`: default entitlement, overtime -> bonus days conversion,
  automatic carryover computation, negative-remaining clamped to 0
  carryover, manual override, JSON persistence round-trip.
- `main_window.py` (full app, headless): startup fetch + budget rendering,
  half-day vacation add + budget update, entitlement field edits +
  persistence, explicit next-year prefetch into cache, simulated year
  rollover, and the phantom-carryover regression test (before/after fix).

## Not yet done / still open
- WSL2 status check and the actual Android APK build (`pyside6-android-deploy`)
  are still pending - blocked on the user running `wsl --status` / `wsl -l -v`
  in PowerShell.
- The toolbar search box still doesn't filter the calendar views (known v1
  gap, unrelated to this batch).
- No live test yet against the real network APIs from the user's own
  machine (only mocked/offline testing so far in this sandbox).
