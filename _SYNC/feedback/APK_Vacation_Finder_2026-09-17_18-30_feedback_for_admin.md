# APK Vacation Finder - Feedback for Admin
**Date:** 2026-09-17 18:30
**Version:** v0.1 (PyModul)

## What changed in this batch

Explicit request: "Daten intern in Datenbank speichern, default 2 Jahre
(aktuelles Jahr + 1)" - persist holiday/school-holiday/subdivision data
in a local database instead of only the in-memory `holidays_by_year`
dict, with a "current year + next year" retention policy, plus an
explicit feasibility question for >90 supported countries.

### Feasibility answer (given before building anything)
~98 countries x 2 years x ~15 holiday entries/country/year ~= 3,000 rows;
school holidays (broken out per subdivision by OpenHolidays) more like
5,000-15,000 rows. Low-single-digit-MB SQLite file - not a concern by
itself. The real constraint is network politeness, not storage: the
cache must stay lazy (only the countries/years the app actually visits -
selected country, comparison country, September prefetch of next year -
never all 98 countries eagerly) rather than becoming a bulk mirror.

### New module: `holiday_cache.py`
- SQLite (stdlib `sqlite3`, no new dependency), stored via
  `QStandardPaths.AppDataLocation` alongside the existing JSON settings
  files, in `holiday_cache.sqlite3`.
- Three tables: `holidays`, `school_holidays`, `subdivisions`.
- `get_cached_*`/`store_*` per table; `prune_to_years(keep_years)` to
  enforce retention; `get_cache_stats()` for diagnostics.
- Per-row staleness TTL (not a hard expiry - a stale row still exists,
  it's just treated as a miss on the next lookup so upstream corrections
  eventually propagate): 14 days for holidays/school holidays, 90 days
  for subdivisions (these almost never change).
- Holidays are keyed by `(country_code, year, source)`, not just
  `(country_code, year)` - caught this myself before shipping: Nager.Date
  and OpenHolidays can disagree slightly on names/coverage, and the UI
  lets the user toggle between them, so the source has to be part of the
  cache key or toggling would silently keep serving the other source's
  cached data for up to the TTL window.
- `prune_to_years()` wired into `main_window.py`'s existing
  `_check_year_rollover_and_prefetch()` (runs hourly, and once at
  startup) - deletes any cached year outside `{current_year,
  current_year + 1}` on every check, so the on-disk cache never grows
  past two years of data even across long-running sessions and year
  rollovers.

### `api_client.py` rewritten
- `fetch_subdivisions`/`fetch_school_holidays`/`fetch_country_holidays`
  now check the cache first, hit the network only on a miss, and store a
  successful network result back to the cache.
- On a network failure, first tries to serve *any* existing cached data
  for that key (even past its normal staleness window) before giving up -
  "a slightly outdated calendar while offline" beats a blank one.
- This also fixes the sole Critical Issue from the earlier code review
  (see the 17-14 feedback log's context): every fetch function used to
  catch `requests.RequestException` internally and return `[]`, which
  made a real network failure indistinguishable from "this country has
  zero holidays" and made `workers.HolidayFetchWorker`'s `failed` signal
  effectively dead code. Network errors from the low-level
  `_fetch_nager_holidays`/`_fetch_openholidays_holidays` functions now
  propagate (after the stale-cache fallback attempt above finds nothing),
  so the UI's existing "Error loading data" path actually fires again.
  This had to be fixed as part of this batch anyway: caching an empty
  `[]` result from a swallowed network error would have poisoned the
  cache with a false "no holidays" answer for the TTL window.

### Bug found and fixed during testing (own testing, not user-reported)
The offline-fallback lookup originally bypassed the staleness check with
`max_age_days=10**9` ("a huge number = never stale"). That overflows
Python's `timedelta` (max ~999,999,999 days) and crashed with
`OverflowError` the moment the fallback path was actually exercised in a
network-failure test. Fixed properly: `holiday_cache._is_stale()` now
treats `max_age_days=None` as the "never stale" sentinel instead of a
big number, and `api_client.py`'s three fallback call sites pass `None`.
Re-tested after the fix - the fallback path now works as intended
instead of only working when never actually triggered.

## Testing performed
All headless (`QT_QPA_PLATFORM=offscreen`, real PySide6, network mocked):
- `holiday_cache.py` scale test using the real 97-country `COUNTRIES`
  list, 2 years, realistic per-country volumes (worst case: Germany with
  16 subdivisions x 6 school-holiday periods): 1.19s write, 2,910 holiday
  rows + 4,800 school-holiday rows + 388 subdivision rows, 944KB file,
  0.25ms/country read. Re-run after adding the `source` column: 0.09s,
  no meaningful regression.
- Source-isolation test: stored different `local_name` values under
  `nager` vs `openholidays` for the same country/year, confirmed each
  source returns its own distinct cached data.
- `api_client.py` functional test (mocked `_fetch_nager_holidays`/
  `_fetch_openholidays_holidays`, isolated SQLite file): cache miss ->
  network fetch -> stored (1 network call); cache hit -> no network call;
  different source -> not served from the other source's cache; network
  failure with no cache at all -> exception propagates (reaches the
  `failed` signal); network failure with an existing cache -> stale data
  served instead of raising. All 5 scenarios pass.
- `main_window.py` smoke test: full `MainWindow` construction headless
  with the new `holiday_cache` import and `prune_to_years()` call wired
  into `_check_year_rollover_and_prefetch()` - constructs and closes
  cleanly, no exceptions.

## Deployed
`api_client.py`, `holiday_cache.py` (new), `main_window.py` ->
`BIN\versions\v0.1\PyModul\`.

## Not yet done / still open
- Still pending from the GitHub Actions cloud-build setup (unrelated to
  this batch): user needs to run `git push -u origin main` from their own
  machine (no credentials available in this sandbox), install + auth the
  GitHub CLI (`gh`), then run `Build-Apk-Cloud.ps1` for a first real
  build - the `build-apk.yml` workflow's `pyside6-android-deploy` CLI
  flags are still TODO-marked pending that first real run.
- Other (non-Critical) code-review Suggestions not yet addressed:
  atomic file writes in `storage.py`/`entitlement.py`/`user_config.py`,
  the unused `MAX_USEFUL_CARRYOVER_YEARS` constant in `entitlement.py`,
  the possible duplicate-fetch race between a manual year-select and the
  background prefetch, and the untranslated `_on_data_failed` error
  string. Never got an explicit answer on whether to fix these now or
  leave the review as a reference - still open.
