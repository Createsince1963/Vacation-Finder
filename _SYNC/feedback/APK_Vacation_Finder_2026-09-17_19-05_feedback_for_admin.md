# APK Vacation Finder - Feedback for Admin
**Date:** 2026-09-17 19:05
**Version:** v0.1 (PyModul)

## What changed in this batch

Two explicit follow-up requests to the SQLite cache batch: since fetching
data isn't a performance concern (per the 18-30 feedback log's scale
test), take the best-performance/best-UX approach and group the country
dropdowns by continent; and define a fixed set of 8 countries to keep
available offline.

### `constants.py`: continent metadata + grouped-country helper
- Every entry in `COUNTRIES` now also carries a `"continent"` key (all 97
  countries classified: Europe 52, North America 12, South America 11,
  Asia 12, Africa 8, Oceania 2). A few transcontinental/borderline cases
  (Russia, Turkey, Georgia, Cyprus) are classified by majority landmass -
  documented in the module docstring as a UI-grouping choice, not a
  geopolitical statement.
- New `CONTINENT_ORDER` (Europe first, then North/South America, Asia,
  Africa, Oceania) and `countries_by_continent()` helper - groups+sorts
  the existing in-memory `COUNTRIES` list, no extra data source, no
  network/DB cost ("beste Performance" here just means: this is pure
  static-data reshaping of data already loaded, so there's no downside to
  always using the friendlier grouped view - no separate "fast" vs "slow"
  mode was needed).
- New `OFFLINE_DEFAULT_COUNTRIES` = `["DE", "AT", "CH", "FR", "IT", "ES",
  "GB", "US"]` - 8 countries. **This exact list is my default pick, not
  something you specified** - a DACH core (Germany/Austria/Switzerland,
  your most likely home/work markets) plus the largest neighbouring
  European economies and the US/UK. Easy to change: it's one list literal
  in `constants.py`, nothing else references specific country codes.

### `main_window.py` wiring
- `country_combo` and `country2_combo` are now built via a shared
  `_populate_country_combo()` helper using a `QStandardItemModel`: each
  continent gets a bold, non-selectable header row, with its countries
  (indented, alphabetical) listed under it. `country2_combo` keeps its
  leading "None" entry above the groups.
- New offline-default prefetch: at startup, after the normal fetch for
  the selected country, a background queue fetches the current year's
  holidays (nationwide, no school holidays/subdivisions - those are
  secondary) for each of the 8 `OFFLINE_DEFAULT_COUNTRIES` not already
  covered by the current selection - **one country at a time**
  (chained via `QThread.finished`, not all 8 in parallel), reusing the
  same `HolidayFetchWorker`/`start_holiday_fetch` used elsewhere. Each
  successful fetch is persisted by `api_client.py`'s existing caching
  (from the previous batch) into `holiday_cache.sqlite3` - that's the
  actual point: by the time the app is opened without a network
  connection, these 8 countries already have cached data for
  `api_client.py`'s stale-cache offline fallback to serve, not just
  whatever the user happened to view last.
- Silent-by-design failure handling (matches the existing September
  prefetch's philosophy): if a given country's fetch fails (e.g. actually
  offline right now), that one is skipped and the queue moves on to the
  next - no error dialog, since this is an unrequested background
  warm-up, and a failure here is exactly the "no network right now"
  situation the warm-up exists to prepare for next time.
- `closeEvent` extended to also wait for/quit this new prefetch thread
  before the window closes (same reasoning as the existing fetch/prefetch
  thread guards - avoids "QThread: Destroyed while thread is still
  running").

## Testing performed
All headless (`QT_QPA_PLATFORM=offscreen`, real PySide6, network mocked
except where noted):
- Grouping: `countries_by_continent()` returns all 97 countries across
  the 6 continent groups with no duplicates/omissions, each group
  alphabetically sorted.
- `country_combo`/`country2_combo`: contain header rows + every country
  code; continent header rows are confirmed non-selectable
  (`Qt.ItemFlag.ItemIsEnabled` unset); `country2_combo` keeps its "None"
  entry.
- Offline-default prefetch, clean-success path (network mocked to
  succeed): all 8 `OFFLINE_DEFAULT_COUNTRIES` (minus whichever matches
  the current selection) get fetched exactly once each, sequentially;
  confirmed a fetched country's data actually lands in
  `holiday_cache.sqlite3` (read back directly, not just checked
  in-memory).
- Offline-default prefetch, failure-resilience path: ran with the real
  (sandboxed, network-restricted) `fetch_school_holidays`/
  `fetch_subdivisions` calls left un-mocked, so every one of the 8
  fetches genuinely failed at the network layer - confirmed the app
  didn't crash, `_on_offline_prefetch_failed` fired for each, and the
  queue still worked through and completed all 8 countries rather than
  stopping at the first failure.
- Full `main_window.py` smoke test still passes (constructs/closes
  cleanly with all of the above wired in).

## Deployed
`constants.py`, `main_window.py` -> `BIN\versions\v0.1\PyModul\`.

## Not yet done / still open
- `OFFLINE_DEFAULT_COUNTRIES` is my best-guess default (see above) - say
  the word if you want a different 8.
- Still pending from earlier batches (unrelated to this one): `git push
  -u origin main` from your own machine, `gh` CLI install + auth, first
  real cloud APK build via `Build-Apk-Cloud.ps1`; the remaining
  non-Critical code-review Suggestions (atomic file writes, the unused
  `MAX_USEFUL_CARRYOVER_YEARS` constant, the prefetch/manual-select race,
  the untranslated error string) - still no explicit go-ahead on those.
