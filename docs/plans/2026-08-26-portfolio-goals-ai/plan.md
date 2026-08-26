# Portfolio goals — richer kinds, projections, AI suggestions — Implementation Plan

> **For Agent:** Execute task-by-task; verify before proceeding; commit after each task.
> **TDD Rule:** No production code without a failing test first.

**Goal:** Three goal kinds with progress + deterministic projections, a redesigned Goals page with a summary hero, an AI suggestions panel (aggregates-only, cached, one-click add), and a nearest-goal line on the Net worth hero.
**Architecture:** Additive goal fields in the Mongo repository → existing goal routes → pure progress/projection helpers in `data.js` → redesigned `GoalsCard`/Goals page. AI: new `webapp/goal_advisor.py` (aggregate → DeepSeek → normalised suggestions, Mongo cache) behind one new route, consumed by a suggestions panel.
**Complexity Path:** `Simplified TDD path` — `tests/e2e` is Streamlit-mocked, no browser harness.
**Status:** Complete
**Branch:** `feat/portfolio-goals-ai`

## Architecture Review
Files that change:
- `webapp/portfolio_repository.py` — goal kinds/fields, baseline capture, legacy default
- `webapp/goal_advisor.py` — **new**: `build_goal_aggregate`, `normalize_suggestions`, `_call_llm`, cache (`ai_goal_suggestions`), `get_suggestions(user, snapshot, force_refresh, dismiss)`
- `webapp/api.py` — `POST /api/portfolio/goals/suggestions`
- `dashboard/app/data.js` — `computeGoalProgress`, `projectGoal`, `pickNearestGoal`
- `dashboard/app/api.js` — `apiGoalSuggestions({force_refresh, dismiss})`
- `dashboard/app/page-portfolio.jsx` — `GoalsCard` → `GoalForm` + `GoalRow` + `GoalsHero` + `GoalSuggestions`; Goals page layout; Net worth hero line
- `dashboard/app/styles.css` — goal card / suggestion card block
- `dashboard/index.html` — cache-busters
- Tests: `tests/unit/test_goal_advisor.py` (new), `tests/integration/test_portfolio_repository.py`, `tests/test_portfolio_api.py`, `dashboard/app/data.test.js`, `dashboard/app/page-portfolio.test.js`

Reused: goal routes + `api.js` goal functions, `allocation`/`assetKinds`/`totals`/`history` already computed in the page, `buildPortfolioNetWorthHistory`, `_portfolioSortedValuations`, `StatBlock`, `.hero*`/`.panel*`/`.seg`/`.btn`/`.tag`/`.hint`, AI Coach's DeepSeek client pattern (`deepseek_config`), `_JsonRequest`/MagicMock-Mongo test helpers.

## Shape — Ladder Pass
| Candidate | Rung reached | Kept / Skipped | Reason (one line) |
|---|---|---|---|
| New goal kinds as new collections | 1 | Skipped | Additive fields on `portfolio_goals` cover it; `skipped: per-kind collections, add when kinds diverge in lifecycle` |
| Server-side progress/projection endpoint | 2 | Skipped | Client already holds assets/debts/histories (original goals decision); `add when a non-JS consumer needs it` |
| Projection math | 6–7 | Kept (least-squares, ~20 lines) | Only stdlib arithmetic; no charting/stats dependency |
| Nearest-goal selection | 6 | Kept | one sort |
| AI client/prompt | 2 | Kept by mirroring `ai_coach.py` | Same client, config, JSON discipline, cache shape — no new dependency |
| Separate dismiss endpoint | 1 | Skipped | `dismiss` is a field on the single suggestions route |
| Server-side stale detection | 1 | Skipped | Client compares snapshot to current net/goal count; `add when snapshot grows beyond two numbers` |
| Goal-kind selector UI | 4 | Kept as `<select>` | Native control |
| Goal card CSS | 7 | Kept small | Existing panel/hero classes cover layout; ~40 lines for card grid, kind tag, projection line |
| Extract `GoalRow`/`GoalForm`/`GoalsHero`/`GoalSuggestions` | 7 | Kept | `GoalsCard` is already 100 lines; the redesign triples it — extraction is the change, not scaffolding |
| Suggestion retry/backoff | 1 | Skipped | 502 + Refresh; `add when DeepSeek rate limits show up` |
| Goal history chart / notifications / ordering | 1 | Skipped | Out of scope per intent |
| Prefactor | — | None | Nothing to untangle first; `GoalsCard` is replaced wholesale in Task 2 |

## Implementation Steps

### Task 1 — Goal kinds end to end
**Delivers:** Create a debt-payoff and an allocation goal from the form and see correct progress; legacy goals unchanged (AC1, AC2, AC3, AC15, AC16). Blocked by: none.
1. RED `tests/integration/test_portfolio_repository.py`: `create_goal` with `kind: debt_payoff, debt_id` reads the debt (`portfolio_debts.find_one`) and stores `baseline` = its value; unknown debt → `ValueError`; `kind: allocation` requires `asset_kind` (validated via `_validate_asset_kind`) and `target_pct` in 1–100; `target_amount` optional for non-net-worth kinds; unknown kind → `ValueError`; `update_goal` ignores/rejects kind change; `_serialize_goal` of a legacy doc yields `kind: "net_worth"`.
2. GREEN `portfolio_repository.py`.
3. RED `tests/test_portfolio_api.py`: POST goal with debt kind passes payload through; invalid → 400 (existing pattern).
4. GREEN (likely no route change; confirm).
5. RED `data.test.js`: `computeGoalProgress(goal, ctx)` for the three kinds — ctx `{net, assetsTotal, allocationByKind, debtsById}`; debt baseline math, allocation band ±2 pp, legacy goal (no kind) = net worth, deleted debt → `{missing: true}`; clamp 0..1.
6. GREEN `data.js` + export.
7. RED `page-portfolio.test.js`: kind `<select>`, debt/class pickers, `computeGoalProgress(` used, "Debt removed" text.
8. GREEN `page-portfolio.jsx`: `GoalForm` with kind selector (net worth: name+amount+date; debt payoff: debt select + date, name defaults to "Pay off {debt}"; allocation: class select + target % + date); rows use `computeGoalProgress`. Keep it inside the current card layout — the redesign comes in Task 2. Bump `page-portfolio.jsx`, `data.js` cache-busters.
9. Gates: `uv run pytest tests/integration tests/unit tests/test_*.py -q`; `for f in dashboard/app/*.test.js; do node --test "$f"; done` (+ `TZ=America/New_York` for data); `npx esbuild dashboard/app/*.jsx --loader:.jsx=jsx --outdir=/tmp/jsxcheck`.
10. Commit `feat(goals): debt-payoff and allocation goal kinds`.

### Task 2 — Projections + Goals page redesign + Net worth line
**Delivers:** Hero, cards with projection text, nearest-goal line (AC4–AC8). Blocked by: Task 1.
1. RED `data.test.js`: `projectGoal(goal, points, {now, current, target})` — rising net worth → ETA ISO date; dated goal → `monthlyNeeded`; <2 points or <30 days → `reason: "not_enough_history"`; slope away from target → `reason: "not_on_track"`; debt payoff uses falling balance; allocation → `null`. `pickNearestGoal(goals, progressById)` → highest progress unfinished, tie by earliest date, none when all done. Dates via ISO string math only; run in both TZs.
2. GREEN `data.js`.
3. RED `page-portfolio.test.js`: `GoalsHero`, `GoalRow`, `projectGoal(`, "not enough history", `pickNearestGoal(`, Net worth hero line (`Next goal`), `pf-goal-` CSS classes present in `styles.css`.
4. GREEN: `GoalsHero` (three `StatBlock`s: Next milestone · ETA · Done N/M), `GoalRow` (kind tag, name, target, progress bar, projection line, edit/remove; "Debt removed" state), Goals page composes hero + rows + form + (Task 3 slot); Net worth hero: one line under `.hero-delta`. `styles.css` block; bump `styles.css`, `page-portfolio.jsx`, `data.js` cache-busters.
5. UI feedback loop (gstack browse, demo user): create three goals (one per kind) with enough history to project; screenshots `goals-page.png`, `goals-form-kinds.png`, `networth-next-goal.png`. 2–3 look-adjust rounds expected.
6. Gates as Task 1. Commit `feat(goals): projections, goals hero and cards, nearest-goal line`.

### Task 3 — AI suggestions end to end
**Delivers:** Panel generates/caches/refreshes suggestions, Add creates a goal, Dismiss persists, stale hint, key-missing note (AC9–AC14). Blocked by: Task 1 (Task 2 for layout slot; can run after 2).
1. RED `tests/unit/test_goal_advisor.py`: `build_goal_aggregate(assets, debts, histories, goals)` returns only the allowed keys — assert no asset `name`/`ticker`/`units` anywhere in the JSON; debts as indexed `{i, kind, balance, apr, monthly}`; allocation as `{kind, name, pct, value}`; 12-month trend `[{date, net}]` reusing month-end logic; existing goals `{kind, target, progress}`. `normalize_suggestions(raw, aggregate, debts, existing_goals)` → drops unknown kind, missing numbers, `target_pct` outside 1–100, debt index out of range, duplicates of existing goals; maps debt index → id; caps at 5, min 3 else returns what's valid; assigns stable ids (hash of kind+target). Cache: `get_suggestions(user, snapshot_ctx, force_refresh=False, dismiss=None)` with MagicMock Mongo — returns cached when present and not forced, filters `dismissed_ids`, `dismiss` appends and returns; `force_refresh` clears dismissals; missing key → `ValueError` before any DB write.
2. GREEN `webapp/goal_advisor.py` (lazy `from openai import OpenAI` inside `_call_llm`; no pandas import).
3. RED `tests/test_portfolio_api.py`: route 503 when advisor raises `ValueError`; 502 on other errors; passes `force_refresh`/`dismiss`; builds the snapshot from `list_portfolio`, `list_valuations`, `list_goals` (patched).
4. GREEN `api.py` route (lazy import of `goal_advisor`, `asyncio.to_thread` for the LLM call).
5. RED `page-portfolio.test.js`: `apiGoalSuggestions(`, `GoalSuggestions`, "Refresh suggestions", "Dismiss", "portfolio changed", "not configured".
6. GREEN `api.js` + `GoalSuggestions` panel (cards: kind tag, name, target, date, rationale, priority; Add → `createGoal` with the suggestion's payload then dismiss it; Dismiss → route; Refresh → `force_refresh`; snapshot time; stale hint when `snapshot.net`≠round(net) or `snapshot.goal_count`≠goals.length; key-missing note on 503). Bump cache-busters.
7. UI feedback loop: live generation once (key is set): screenshots `goals-suggestions.png`, `goals-suggestion-added.png`; also the 503 note by temporarily unsetting the key in a second server run if cheap, else code-path evidence via test.
8. Gates as Task 1. Commit `feat(goals): AI goal suggestions from portfolio aggregates`.

## Testing Strategy
- Python fast loop: `uv run pytest tests/integration tests/unit tests/test_*.py -q` (now ~4 s after the `test_db` fix).
- JS: all `dashboard/app/*.test.js`; `data.test.js` also under `TZ=America/New_York`.
- Syntax: esbuild over all JSX. Lint: `uvx ruff format --check` on new/changed Python.

## Risks & Mitigations
- **Riskiest: Task 3's model output quality** (nonsense targets, duplicates) → the normaliser is the guardrail and is fully unit-tested; UI shows rationale so users can judge.
- **`pandas` stub in `tests/test_portfolio_api.py`** → `goal_advisor` imports no pandas and is lazy-imported in the route.
- **Baseline capture needs the debt at creation** → repository reads `portfolio_debts` inside `create_goal`; tests mock `find_one`.
- **Date math** → ISO-string arithmetic only; both-TZ test runs (CLAUDE.md lesson).
- **Page size** — `page-portfolio.jsx` is already >1,300 lines; the redesign adds ~250. Mitigation: extract the four goal components cleanly so a later move to its own file is a cut/paste (recorded, not done now).
- **Blocking LLM call in async route** → `asyncio.to_thread` (CLAUDE.md lesson).

## Success Criteria
- [x] AC1–AC16 demonstrated (tests + screenshots; Spec axis: 15 Met, AC8 fixed in the fix pass)
- [x] Existing goal tests still green; legacy goals render unchanged
- [x] Aggregate sent to the AI contains no asset names/tickers/units (test asserts)
- [x] Verification output pasted in Progress Log
- [x] Tri-axis review + fix-pass verification recorded

## Progress Log
| Date | Task | Status | Notes |
|---|---|---|---|
| 2026-08-26 | Phase 0–2 | Done | intent.md confirmed; test points confirmed; spec.md saved |
| 2026-08-26 | Interrogation pass | Done | 4 findings fixed: (1) `goal_advisor` must not import pandas and must be lazy-imported in the route (pandas stub in route tests); (2) debt baseline capture requires reading the debt in `create_goal` — test mocks stated; (3) legacy docs without `kind` — serializer default made explicit in Task 1; (4) cache-buster bumps listed per task; Task 3 dependency on Task 2 clarified as layout-only. |
| 2026-08-26 | Task 1 | Done | Repository: `kind` (default `net_worth`), `_goal_kind_fields` (debt baseline read from `portfolio_debts` at creation + default name "Pay off {debt}"; allocation `asset_kind` via `_validate_asset_kind`, `target_pct` 1–100, default name "{Class} at N%"), kind immutable on update, `target_pct` editable. Routes unchanged (payload pass-through). `data.js` `computeGoalProgress` (net worth / debt baseline / allocation ±2 pp band; `missing` for deleted debt). `GoalsCard` → `GoalForm` (kind select swaps fields) + kind tag + per-kind target text; `goalCtx` memo in the page. CSS `.pf-goal-form`; cache-busters page-portfolio v11, data v6, styles v10. Evidence: Python fast loop **182 passed**; JS data 25 (both TZ), portfolio 19, others green; esbuild 0 errors. Old regex test asserting inline `Math.min(1,` replaced by a helper-usage assertion (math now tested in data.test.js). |
| 2026-08-26 | Task 2 | Done | `data.js`: `projectGoal` (least-squares per day over ISO-day numbers, ≥2 points ≥30 days, reasons ok/done/not_enough_history/not_on_track/n/a, `monthlyNeeded` from target date) and `pickNearestGoal`. UI: `GoalsHero` (3 `StatBlock`s), `GoalRow` cards (kind tag, bar, target text, projection line, Debt-removed state), `GoalsCard` sorts open-by-progress then done; `PortfolioPage` gains `onNavigate` (shell passes `navigate`) for the Net-worth "Next goal" line. CSS `.pf-goal-*`, `.pf-next-goal`. Cache-busters: page-portfolio v12, data v7, styles v11, shell v6. Look-adjust: 2 rounds (subtitle; pace wording/rounding). Evidence: data 28 pass (both TZ), portfolio 20, all JS green, esbuild 0 errors; `goals-page.png` (hero + 4 cards incl. projections "On this trend: 2027-07-23 · Add 2,400.00/month…"), `goals-form-kinds.png` (kind select swaps to debt picker), `networth-next-goal.png` ("Next goal · Equities at 35% · 80%"). Server restarted for Task 1 Python. Demo data seeded on `trend-demo@local.test` (2 assets, 1 debt, 4 goals) — to be deleted at the end. |
| 2026-08-26 | Task 3 | Done | `webapp/goal_advisor.py`: `build_goal_aggregate` (totals, allocation %, indexed debts w/o names, month-end net-worth trend, existing-goal progress; test asserts no names/tickers/units in the JSON), `normalize_suggestions` (kinds, ranges, debt index→id, dedupe vs existing, stable 12-char ids, cap 5, priority default medium), `_call_llm` (DeepSeek, lazy openai import), per-user Mongo cache `ai_goal_suggestions` with `dismissed_ids`, `force_refresh` resets dismissals, **per-user generation lock** (added after observing two concurrent POSTs; 3-thread test → 1 model call). Route `POST /api/portfolio/goals/suggestions` builds the snapshot server-side (portfolio + valuations + goals + asset-type names), `asyncio.to_thread`, 503 no key / 502 fixed message. UI: `apiGoalSuggestions`, `GoalSuggestions` panel (priority-coloured cards, rationale, Add → create goal then dismiss, Dismiss, Refresh, cached/snapshot time, stale hint, not-configured note). CSS `.pf-sugg-*`. Cache-busters page-portfolio v13, api v6, styles v12. Evidence: fast loop **191 passed**, advisor 7 pass, route +2; JS all green (data also NY TZ); esbuild 0. Live: first generation 98 s (DeepSeek v4 pro JSON) → 3 suggestions (80k by 2027-02 medium; 90k stretch high; cash to 60% low) `goals-suggestions.png`; Add → POST goals 200, goal count 4→5, re-fetch with dismiss 1.06 s; Dismiss → card removed; stale hint shown after goal count changed `goals-suggestion-added.png`. 503 path covered by route test (not exercised live). |
| 2026-08-26 | Tri-axis review (Opus 5; session authored on Fable) | Done | **Standards: Warn** — HIGH every `ValueError` (incl. `JSONDecodeError`) mapped to 503 "not configured" and the UI then hid Refresh; MEDIUM `dismiss` unvalidated into `$addToSet`; MEDIUM snapshot (N+3 queries) built before the cache is consulted; MEDIUM no DeepSeek client timeout; MEDIUM progress/projection computed twice; MEDIUM `page-portfolio.jsx` 1,590 lines; nits (dead `_GOAL_KINDS`, generator scaffold, server/JS progress divergence, comparator tie, `list_goals` sort). **Spec: Warn** — AC1–7, 9–16 Met; AC8 Partially (no ETA fallback on the Net-worth line); Task 1 route test dropped unrecorded; demo cleanup open; nits (in-band progress = 1 vs spec formula, stale hint after Add, 503 detection, signature drift, unfinished log sentence). **Simplicity: Warn** — MEDIUM duplicated results/projections, server-side `_goal_progress` duplicating the JS helper (and diverging on the ±2 pp band), per-user lock table, route re-declaring kind names, generator scaffold; nits (`SUGGESTION_KIND_TAG`, `default_name` smuggled in dict, nested ternary, inline styles, one-key dict). |
| 2026-08-26 | Fix pass | Done | `AdvisorNotConfigured(ValueError)` → only it maps to 503 (test: JSON `ValueError` → 502); UI keys "not configured" off the message and keeps Refresh otherwise. `dismiss` must be a string (400 otherwise; test). `get_suggestions(user, build_portfolio)` takes a zero-arg builder called only inside generation (test: cached reads never build; route test calls the builder inside the patches). `OpenAI(..., timeout=180)` (test). Single module `_GEN_LOCK` with corrected `ponytail:`; 3-thread test unchanged. `existing_goals` now `{kind, target}` only — `_goal_progress` deleted, `_goal_target` helper. Generator scaffold → plain loop. Route passes only custom asset-type names. Repository: `_goal_kind_fields` returns `(fields, default_name)`; dead `_GOAL_KINDS` removed; one-key dict → conditional. Goals UI moved to **`dashboard/app/page-goals.jsx`** (305 lines; `page-portfolio.jsx` 1,590 → 1,285) loaded before page-portfolio; `GoalsCard` receives `resultsById`/`projectionsById` computed once in `PortfolioPage`; shared `goalKindTag`; `pickNearestGoal` comparator returns 0 on ties then id. AC8: Net-worth line falls back to "no date yet" / "no projection for allocation goals". Added goal-route 400 test. Cache-busters: page-goals v1, page-portfolio v14, data v8. **Declined (recorded):** stale hint right after Add (spec-literal AC12); in-band progress forced to 1 (deliberate: "done" reads 100%); `list_goals` server sort (client re-sorts); inline layout styles (file convention); `ai_coach.py` timeout (other module — follow-up). Evidence: fast loop **195 passed** ×2; JS 4/29/5/21/1 (data also NY TZ); esbuild 0 errors. UI re-verified after the split: `goals-page.png` (identical render from page-goals.jsx; cached suggestions 577 ms — lazy snapshot), `networth-next-goal.png` ("Next goal · Equities at 35% · 80% · no projection for allocation goals"). |
| 2026-08-26 | Fix-pass verification (Opus 5) | Done | Verdict **Clean with nits** — 11/12 Addressed; item 10 partial (`page-portfolio.jsx` 1,285 lines, pre-existing overage; `ValuationPanel`/`HoldingMarketPanel` are the next lift-out — follow-up). New: MEDIUM module lock could pin executor threads behind a 180 s generation; LOW `dismiss` length unbounded; nits (route test proves builder output not laziness; goal-route test mocks the repository; `_goal_target` int/float). Checks: 195 pass; JS all green; esbuild clean incl. `page-goals.js`. |
| 2026-08-26 | Fix pass #2 | Done | `_GEN_LOCK.acquire(timeout=5)` → `AdvisorBusy` → **429** (tests: held lock raises; route maps 429); `dismiss` capped at 64 chars (test); `_goal_target` returns `0.0`. Fast loop **197 passed**; JS all green; esbuild 0. Nits declined: route-level laziness assert (advisor test proves it), repository reach-through in the route test (repository has its own kind tests). |
| 2026-08-26 | Cleanup + Complete | Done | Demo user `trend-demo@local.test`: 5 goals, 2 assets, 1 debt deleted via API; `ai_goal_suggestions` cache doc deleted (1). CLAUDE.md learn-back: map only your own exception types to client-facing statuses (seen twice: `KeyError⊂LookupError`, `JSONDecodeError⊂ValueError`). Follow-ups noted, not done: `ai_coach.py` client timeout; lift `ValuationPanel`/`HoldingMarketPanel` out of `page-portfolio.jsx`. Merge to `main` on user instruction. |
