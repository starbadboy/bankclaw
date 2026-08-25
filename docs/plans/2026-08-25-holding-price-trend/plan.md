# Holding price & market-value trend — Implementation Plan

> **For Agent:** Execute task-by-task; verify before proceeding; commit after each task.
> **TDD Rule:** No production code without a failing test first.

**Goal:** In a holding's valuation panel, let the user set Ticker + Units and see a Price | Value line chart (S$, 1M/3M/1Y/All) fetched from yfinance, display-only.
**Architecture:** FastAPI route → new `webapp/market_data.py` (yfinance adapter + pure series builder + TTL cache) → `dashboard/app/api.js` → `page-portfolio.jsx` ValuationPanel (reusing `NetWorthChart` and `.seg` pills) with a pure series helper in `data.js`.
**Complexity Path:** `Simplified TDD path` — `tests/e2e` is Streamlit-mocked, not a browser harness.
**Status:** Complete
**Branch:** `feat/holding-price-trend`

## Architecture Review
Files that change:
- `pyproject.toml` / `uv.lock` — add `yfinance`
- `webapp/portfolio_repository.py` — `units` on `create_asset` / `update_asset`
- `webapp/market_data.py` — **new**: `build_market_series()`, `fetch_history()` (lazy yfinance import), `get_market_history()` with TTL cache
- `webapp/api.py` — `GET /api/portfolio/assets/{asset_id}/market-history`
- `dashboard/app/api.js` — `apiFetchAssetMarketHistory(id, range)`; export
- `dashboard/app/data.js` — `buildHoldingChartData(points, mode)`; export
- `dashboard/app/page-portfolio.jsx` — `NetWorthChart` tweaks; `ValuationPanel` Market data row + chart + pills; wire `handleUpdateAssetMarket`
- `dashboard/index.html` — bump `?v=` on `data.js`, `api.js`, `page-portfolio.jsx`
- Tests: `tests/unit/test_market_data.py` (new), `tests/test_portfolio_api.py`, `tests/integration/test_portfolio_repository.py`, `dashboard/app/data.test.js`, `dashboard/app/page-portfolio.test.js`

Reused as-is: `PATCH /api/portfolio/assets/{id}` + `apiUpdatePortfolioAsset`, `.seg` pill CSS, `_fetch`/`_portfolioMutate`, `fmtSGD`, `_JsonRequest` test stub, MagicMock-Mongo test helper.

## Shape — Ladder Pass
| Candidate | Rung reached | Kept / Skipped | Reason (one line) |
|---|---|---|---|
| New line-chart component | 2 (reuse) | Kept as 2 tweaks to `NetWorthChart` | Already responsive/area/ticks; only needs empty-label skip + tick formatter |
| Range pill 1M/3M/1Y/All | 2 (reuse) | Kept | `.seg` + `PERF_WINDOWS` pattern already on the page |
| Price/Value toggle | 2 (reuse) | Kept | Same `.seg` pattern, two buttons |
| Ticker/Units save | 2 (reuse) | Kept | Existing PATCH route + `apiUpdatePortfolioAsset`; only `units` field is new |
| Market-data feed | 7 (new dep) | Kept | User decision: yfinance; no installed dep covers price history |
| FX conversion | 7 | Kept | User decision; same feed, `{CUR}SGD=X`, forward-fill in the pure builder |
| TTL cache | 6–7 | Kept (dict + `time.monotonic`) | ~8 lines; `skipped: Mongo-backed cache, add when multi-worker` |
| "All" downsampling | 6 | Kept as one param | `interval="1wk"` when period is `max` |
| Ticker/Units on add-asset form | 1 | Skipped | Out of scope per intent; `add when users ask to set them at creation` |
| Hover tooltip on chart | 1 | Skipped | Last-value label already on `NetWorthChart`; `add when asked` |
| Retry/backoff on feed errors | 1 | Skipped | Inline error + 1h cache suffice; `add when Yahoo rate-limits show up in logs` |
| Loading spinner component | 4/6 | Kept as text "Loading prices…" | Plain text, no component |
| Debt market data | 1 | Skipped | Out of scope |
| Prefactor `NetWorthChart` | — | Kept, first step of Task 2, separate commit | Behaviour-neutral; existing net-worth chart renders identically |

## Implementation Steps

### Task 1 — Market data row: ticker + units end to end
**Delivers:** In the valuation panel the user sets Ticker and Units; they persist and pre-fill on reopen (AC1, AC8, AC11). Blocked by: none.
1. RED — `tests/integration/test_portfolio_repository.py`: `create_asset` stores `units` as float; `update_asset` with `units: "abc"` / `-1` raises `ValueError`; `update_asset` with `units: 672` sets it.
2. GREEN — `portfolio_repository.py`: parse `units` via `_coerce_value` (≥ 0) in both paths; include in create doc (default `None`).
3. RED — `page-portfolio.test.js`: source has `Market data`, `Ticker`, `Units`, `apiUpdatePortfolioAsset`, `handleUpdateAssetMarket`.
4. GREEN — `page-portfolio.jsx`: `ValuationPanel` gets `onUpdateMarket` prop and a "Market data" row (ticker text input, units decimal input, Save button, disabled while busy; only rendered for `itemType === "asset"`). Page adds `handleUpdateAssetMarket` → `apiUpdatePortfolioAsset(id, {ticker, units})` → replace asset in `assets` state. Bump `page-portfolio.jsx?v=6` in `index.html`.
5. Syntax gate: `npx esbuild dashboard/app/*.jsx --loader:.jsx=jsx --outdir=/tmp/jsxcheck`; run `uv run pytest tests/integration tests/unit tests/test_*.py`; `node --test dashboard/app/page-portfolio.test.js`.
6. Commit `feat(portfolio): ticker and units on the valuation panel`.

### Task 2 — Price / Value chart end to end
**Delivers:** Chart with Price | Value toggle and 1M/3M/1Y/All pill, S$-converted, cached, with error state (AC2–AC7, AC9, AC10). Blocked by: Task 1.
1. Prefactor (separate commit): `NetWorthChart` skips x-labels where `d.label` is falsy and accepts `fmtTick` (default keeps `Nk`). Existing tests + net-worth chart unchanged. Commit `refactor(portfolio): NetWorthChart sparse labels and tick formatter`.
2. `uv add yfinance`.
3. RED — `tests/unit/test_market_data.py` for `build_market_series(closes, fx, units, currency)`:
   - USD: value = close × latest FX on/before date; FX gap forward-fills; date before first FX uses first FX.
   - SGD: `fx=None` → price unchanged.
   - Output keys `date, price, value`, dates ISO strings, chronological, rounding to 4 dp price / 2 dp value.
   - `get_market_history` cache: patched `fetch_history` called once for two calls with same (ticker, range); called again after TTL (patch `time.monotonic`).
   - Bad range → `ValueError`.
4. GREEN — `webapp/market_data.py`: `RANGES = {"1M": ("1mo","1d"), "3M": ("3mo","1d"), "1Y": ("1y","1d"), "All": ("max","1wk")}`; `fetch_history(ticker, range)` lazy-imports yfinance, returns `(currency, {iso_date: close})`, raises `LookupError` on empty frame / missing currency; `build_market_series` pure; `get_market_history(ticker, units, range)` composes + cache (`# ponytail: per-process dict cache, Mongo if multi-worker`).
5. RED — `tests/test_portfolio_api.py`: route returns 400 when asset lacks ticker/units; 502 when `get_market_history` raises `LookupError`; happy path returns `{ticker, currency, units, points}`; 400 for bad range.
6. GREEN — `webapp/api.py`: route loads the asset via `list_portfolio(user)["assets"]` lookup by id (or a small `get_asset` in the repository if cleaner — decide at GREEN, prefer no new repo fn), validates, calls `get_market_history`, maps `LookupError`/network `Exception` → 502.
7. RED — `data.test.js`: `buildHoldingChartData(points, "price"|"value")` returns `[{label, value}]`; label is `MMM YY`-style only at month boundaries else `""`; empty input → `[]`. Run under local TZ and `TZ=America/New_York`.
8. GREEN — `data.js` + export.
9. RED — `page-portfolio.test.js`: source has `apiFetchAssetMarketHistory`, `buildHoldingChartData`, `HOLDING_RANGES`, `Loading prices`, `Price`, `Value`.
10. GREEN — `api.js`: `apiFetchAssetMarketHistory(id, range)` + export. `page-portfolio.jsx`: in `ValuationPanel` state `{mode:"value", range:"1Y", data, error, loading}`; effect fetches when `item.ticker && item.units` and on range change; render header "`{ticker} · {currency}{currency!=="SGD" ? " → S$" : ""}`", two `.seg` groups, `NetWorthChart` with `fmtTick` (`S$` compact) or inline error/loading text. Bump `data.js?v=3`, `api.js?v=5`, `page-portfolio.jsx?v=7`.
11. Syntax gate + all tests (`uv run pytest tests/integration tests/unit tests/test_*.py`; JS tests; esbuild; `uv run ruff check .`).
12. UI feedback loop: start server (`uv run uvicorn webapp.api:app --port 8501` per prior session notes), demo login, set ADSK ticker/units, screenshot panel in Value/1Y, Price/3M, and an unknown-ticker error state via gstack `/browse`. Save PNGs in this folder.
13. Commit `feat(portfolio): price and market-value trend in the valuation panel`.

## Testing Strategy
- Fast loop: `uv run pytest tests/integration tests/unit tests/test_*.py` (CLAUDE.md: full suite > 2 min and ordering-sensitive).
- JS: `for f in dashboard/app/*.test.js; do node --test "$f"; done` and again with `TZ=America/New_York`.
- Syntax: `npx esbuild dashboard/app/*.jsx --loader:.jsx=jsx --outdir=/tmp/jsxcheck`.
- Lint: `uv run ruff check .`.

## Risks & Mitigations
- **yfinance / Yahoo instability** (riskiest external): adapter isolated in one function; errors → 502 + inline message; 1h cache limits calls.
- **`pandas` stub in `tests/test_portfolio_api.py`** poisons any module importing yfinance at import time → lazy import inside `fetch_history`.
- **FX date misalignment** (NY vs London tz, holidays): dates as ISO strings from the feed, forward-fill in the pure builder, covered by unit tests.
- **JS date pitfalls** (CLAUDE.md lesson): labels derived from ISO string slices only; run tests under `TZ=America/New_York`.
- **"All" size**: weekly interval bounds ~2k points; SVG path fine.
- **Cache in multi-worker deploy**: per-process only, marked `ponytail:`.

## Success Criteria
- [x] AC1–AC11 demonstrated (tests + screenshots; Spec axis AC table: all Met)
- [x] Existing portfolio tests unchanged and green (34 → 37 Python in the portfolio suites; JS 50 across 5 files)
- [x] Net-worth chart renders identically after the prefactor (`buildPortfolioNetWorthHistory` always emits a label; new props default-neutral)
- [x] Verification commands' output pasted in Progress Log
- [x] Tri-axis review findings recorded

## Progress Log
| Date | Task | Status | Notes |
|---|---|---|---|
| 2026-08-25 | Phase 0–2 | Done | intent.md confirmed; test points confirmed; spec.md saved |
| 2026-08-25 | Interrogation pass | Done | 3 findings fixed: (1) yfinance must be lazy-imported or route tests that stub pandas break; (2) 404-vs-400 for missing asset made explicit (follow existing ValueError→400 convention); (3) `index.html` cache-buster bumps were missing from tasks |
| 2026-08-25 | Task 1 | Done | units on create/update_asset (6-dp, ≥0); Market data row + `handleUpdateAssetMarket` in ValuationPanel; `page-portfolio.jsx?v=6`. Evidence: integration+api tests 14+N pass; `node --test page-portfolio.test.js` 13/13; esbuild clean. Fast loop `uv run pytest tests/integration tests/unit tests/test_*.py` → 144 passed, 17 failed — all 17 = `ServerSelectionTimeoutError localhost:27017` in test_history/test_visualizations (no local Mongo; pre-existing, 30 s each → 11 min run). |
| 2026-08-25 | Task 2 | Done | Prefactor commit ca26784 (NetWorthChart `fmtTick`, empty-label skip). `uv add yfinance`. `webapp/market_data.py` (pure `build_market_series`, lazy-yfinance `fetch_history`, 1h dict cache), `GET /api/portfolio/assets/{id}/market-history?range=`, `apiFetchAssetMarketHistory`, `buildHoldingChartData` (month/year boundary labels, `maxLabels`, leading-label suppression), panel chart with Value/Price + 1M/3M/1Y/All `.seg` pills; NetWorthChart gained default-neutral `fmtValue` + `padFraction`. Cache-busters: data.js v3, api.js v5, page-portfolio v7. Look-adjust rounds: 2 (label overlap, flattened y-range). |
| 2026-08-25 | Task 2 evidence | Done | Python: `tests/unit/test_market_data.py` 7 pass, `tests/test_portfolio_api.py` +4 pass; fast loop → **155 passed, 17 failed** (same 17 pre-existing `localhost:27017` timeouts in test_history/test_visualizations; `--ignore` does not apply to explicitly globbed files). JS: api 4, data 23 (also under `TZ=America/New_York`), insights 5, portfolio 16, transactions 1 — all pass; esbuild clean. UI (gstack browse, demo user `trend-demo@local.test`): `panel-value-1y.png`, `panel-price-3m.png`, `panel-error.png` (502 → inline message). Live: PATCH 200 → `market-history?range=1Y` 200 in 3.9 s first hit, 122 ms cached; `range=3M` 417 ms; last market value S$216,999 vs recorded 216,505. Dev server restarted (it ran without `--reload`). |
| 2026-08-25 | Tri-axis review | Done | Reviewers ran on **Opus 5** (session authored on Fable; authoring model does not review itself). **Standards: Warn** — HIGH blocking yfinance I/O in `async def` route; HIGH unbounded `_CACHE`; MEDIUM ticker charset unvalidated before outbound URL; MEDIUM `padFraction` branch drops padding floor (NaN path on zero-units); MEDIUM empty FX dict silently converts at 1.0; MEDIUM `GBp`-style minor-unit currencies; nits N1–N5. **Spec: Warn** — all AC1–AC11 Met, stories 1–12 satisfied, out-of-scope clean; MEDIUM feed `ValueError` mapped to 400 not 502; MEDIUM zero-units/empty-points chart; nits (unlogged `build_market_series(closes, fx, units)` signature departure — currency handled by the caller; success criteria unticked; non-numeric units message; cropped error screenshot). **Simplicity: Approve** — MEDIUM heuristic missing `ponytail:`; MEDIUM hand-rolled TTL dict vs `lru_cache`; nits (unused `pf-market-*` hooks, verbatim-source regex, magic 36/0.4, reuse `priced`, `padFraction` sentinel). |
| 2026-08-25 | Fix pass | Done | `await asyncio.to_thread(get_market_history…)`; `lru_cache(maxsize=256)` on `(ticker, range, hour-bucket)` + `clear_cache()`; `_clean_ticker` regex `^[A-Z0-9.^=\-]{1,16}$` + upper-case at the repository; range validated in the route, feed errors (incl. library `ValueError`) → 502; `Number.EPSILON` padding floor; empty-points hint; empty FX → `LookupError`; `_MINOR_UNITS` GBp/ZAc/ILA scaling; `ponytail:` on label heuristic; named `_HOLDING_YEAR_LABEL_MONTHS`/`_HOLDING_CROWDED_FIRST_LABEL`; market block extracted to `HoldingMarketPanel` (same file); `pf-market-*` hooks dropped; "Units must be a number"; negative-zero tick. **Declined (recorded):** unknown ticker → 400 (spec pins 502 for unknown ticker); `maxLabels: 0` edge (nonsense input); `padFraction` sentinel (one tested line); separate file for `HoldingMarketPanel` (would add an `index.html` script tag; file was already over 800 lines before this branch). Evidence: portfolio suites 37 pass; JS 4/23/5/17/1 pass (data also under `TZ=America/New_York`); esbuild clean; `uvx ruff format --check` clean on new code (remaining hunks pre-date branch). UI re-verified after server restart: `panel-zero-units.png` (flat S$0.00 line, no `NaN` in any `<path d>`), `panel-value-1y.png`, `panel-error.png` (full panel: 502 message with form + history intact); `range=5Y` → 400; `adsk` stored as `ADSK`; `NOPE_ZZZ` rejected 400 by charset. Demo asset deleted afterwards (demo portfolio 0 assets). |
| 2026-08-25 | Fix-pass verification #1 (Opus 5) | Done | Verdict **Clean with nits** — all 9 findings Addressed. Two Important follow-ups: (a) `fmtValue` assertion had been loosened to `/fmtValue/` with no cause; (b) ticker validated on write only — rows saved before the regex still reach yfinance unvalidated. Nits: `key={item.id}` can replace the manual reset effect (and fixes a pre-existing stale-chart flash); 502 detail echoes raw exception text; hour-bucket vs sliding TTL benign; regex probe of 23 Yahoo shapes — only 19-char option chains rejected. Checks: 37 Python pass; JS 4/23/5/17/1; esbuild clean. |
| 2026-08-25 | Fix pass #2 | Done | Restored the verbatim `fmtValue` default assertion. `TICKER_PATTERN` moved to `market_data` and shared with the repository; `get_market_history` rejects unsafe tickers before fetching (test asserts feed not called). `HoldingMarketPanel key={item.id}` replaces the reset effect. Route: `MarketDataError(LookupError)` introduced because `KeyError ⊂ LookupError` leaked internal messages — only `MarketDataError`/`ValueError` text is echoed; other exceptions log a warning and return a fixed "Market data unavailable". Evidence: portfolio suites **39 pass**; JS all green; esbuild clean; `uvx ruff format --check` clean on new files (remaining hunks/I001 predate the branch). Server restarted; `market-history` for a missing asset → 400. |
| 2026-08-25 | Fix-pass verification #2 (Opus 5) | Done | Verdict **New problems** — 4/4 follow-ups landed, but: read-path guard rejected legacy lowercase tickers (`d05.si` → 502); `MarketDataError` raise asserted only via base `LookupError` (test passed against old code); `except (MarketDataError, ValueError)` still echoed library `ValueError` text. Nits: misplaced `assert_not_called()`; key-remount also resets chartMode/range on asset switch (accepted: switching asset → default view is desirable). |
| 2026-08-25 | Fix pass #3 | Done | `get_market_history` upper-cases before matching (test: `d05.si` → feed called with `D05.SI`); route pre-validates the stored ticker → 400 with an actionable message and passes the upper-cased symbol; echo branch narrowed to `MarketDataError` only (test: library `ValueError` → fixed "Market data unavailable"); tests assert `MarketDataError` directly and fakes raise it; `assert_not_called()` moved inside the patch. Evidence: portfolio suites **40 pass**; JS all green; esbuild 0 errors; ruff format clean on new files. |
| 2026-08-25 | Fix-pass verification #3 (Opus 5) | Done | Verdict **Clean with nits** — 3/3 Addressed; 40 Python pass. Nits applied in the closing commit: `ticker.upper()` without `str()` (a `None` would otherwise become symbol "NONE"); panel headers show `market.data?.ticker \|\| item.ticker` so legacy lowercase rows display the normalised symbol; `never.assert_not_called()` moved inside its patch block. |
| 2026-08-25 | Complete | Done | Branch `feat/holding-price-trend`: plan → Task 1 → prefactor → Task 2 → review fixes ×3, each verified. Final: portfolio suites 40 pass; JS 4/23/5/17/1; esbuild 0 errors; screenshots `panel-value-1y.png`, `panel-price-3m.png`, `panel-error.png`, `panel-zero-units.png`. Learn-back committed to CLAUDE.md (async blocking I/O; Mongo-bound tests). Merge/PR left to the user. |
