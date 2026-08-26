# Goal form redesign — labelled fields + live progress preview — Implementation Plan

> **For Agent:** Execute task-by-task; verify before proceeding; commit after each task.
> **TDD Rule:** No production code without a failing test first.

**Goal:** Add form + Edit mode on the Goals page adopt the Assets-tab labelled form idiom, with a live mini-card preview of the draft goal computed from today's portfolio.
**Architecture:** UI-only change in `dashboard/app/page-goals.jsx` — `GoalForm` rebuilt on `.pf-add-row`/`.pf-add-grid`; a small `GoalPreview` renders `computeGoalProgress(draft, goalCtx)` with the existing bar/target-text pieces; `GoalRow`'s edit branch reuses the same labelled fields and preview. `GoalsCard` passes `goalCtx` (already computed in `PortfolioPage`) down. Small CSS block in `styles.css`; cache-busters in `index.html`.
**Complexity Path:** Simplified TDD — no browser E2E harness in this repo (`tests/e2e` is Streamlit-mocked).
**Status:** In progress
**Branch:** `feat/goal-form-redesign` (created from `main` at 0e1a00c)

## Architecture Review
Files that change:
- `dashboard/app/page-goals.jsx` — `GoalForm` (labelled grid + preview), new `GoalPreview`, `GoalRow` edit branch (labelled + live bar), `GoalsCard` prop plumbing
- `dashboard/app/page-portfolio.jsx` — pass `goalCtx` into `GoalsCard` (one prop)
- `dashboard/app/styles.css` — `.pf-goal-form` block (grid columns for the goal fields, preview spacing); reuse `.pf-add-row`/`.pf-add-grid` rules
- `dashboard/index.html` — cache-busters page-goals v2, page-portfolio v15, styles v13
- `dashboard/app/page-portfolio.test.js` — assertions for the new shape

Reused: `computeGoalProgress`, `goalCtx`, `goalTargetText`, `.pf-goal-bar`/`.pf-goal-pct`/`.pf-goal-meta`, `.pf-add-row`/`.pf-add-grid`/`.pf-add-actions`, `Icon`, `fmtSGD`.

## Shape — Ladder Pass
| Candidate | Rung reached | Kept / Skipped | Reason (one line) |
|---|---|---|---|
| New form CSS system | 2 | Skipped | `.pf-add-row`/`.pf-add-grid`/`.pf-add-actions` already define the labelled idiom; `skipped: goal-specific form styles, add when the grid columns can't be expressed with one modifier class` |
| Preview progress math | 2 | Kept by reuse | `computeGoalProgress(draft, goalCtx)` — no new math; debt draft gets `baseline = debt.value` |
| Preview markup | 2/7 | Kept small | Reuse `.pf-goal-bar`, `.pf-goal-pct`, `goalTargetText`; ~25 lines for `GoalPreview` |
| Shared `GoalFields` component for create + edit | 1 | Skipped | Create and edit differ (kind picker, debt/class pickers only on create); two `<label>` blocks are shorter than a parameterised component; `add when a third form appears` |
| Projection in preview | 1 | Skipped | Out of scope per intent |
| Collapsed/modal form | 1 | Skipped | Decided inline |
| Debounce preview recompute | 1 | Skipped | `computeGoalProgress` is O(1); React re-render per keystroke is fine |
| Prefactor | — | None | `GoalForm`/`GoalRow` already extracted last round; nothing to untangle |

## Implementation Steps

### Task 1 — Labelled add form + live preview (AC1–AC6, AC8)
**Delivers:** The add form in the labelled idiom with a preview card that tracks the draft. Blocked by: none.
1. RED `page-portfolio.test.js`: goals source has `function GoalPreview`, `computeGoalProgress(` inside `page-goals.jsx`, `className="pf-add-grid pf-goal-form"` (or equivalent), captions `<span>Goal kind</span>`, `<span>Target date</span>`, "Reached", "baseline"; `GoalsCard` receives `goalCtx`; `page-portfolio.jsx` passes `goalCtx={goalCtx}`; index.html has `page-goals.jsx?v=2`. Run → fails.
2. GREEN `page-goals.jsx`: `GoalPreview({ draft, goalCtx, assetKinds, privacy })` — builds the draft goal (debt: `baseline` = chosen debt's value), calls `computeGoalProgress`, renders kind tag + name, `.pf-goal-bar`, `.pf-goal-pct` (`Reached` / `N%` / "Enter a target" when target empty), `goalTargetText` line (debt: "… · baseline set when you save"). `GoalForm` rebuilt as `<form className="pf-add-row">` → `<div className="pf-add-grid pf-goal-form">` with `<label><span>…</span>…</label>` per field, kind-specific fields swap inside the grid, `<div className="pf-add-actions">` with the button; error hint below. `GoalsCard` accepts `goalCtx` and passes it to `GoalForm`. `page-portfolio.jsx` passes `goalCtx`. CSS: `.pf-goal-form { grid-template-columns: … }` modifier + `.pf-goal-preview` spacing (~10 lines). Bump cache-busters.
3. Gates: `node --test dashboard/app/page-portfolio.test.js`; `npx esbuild dashboard/app/*.jsx --loader:.jsx=jsx --outdir=/tmp/jsxcheck`.
4. Commit `feat(goals): labelled add-goal form with live progress preview`.

### Task 2 — Edit mode in the same idiom with live bar (AC7)
**Delivers:** Editing a card shows captioned fields and the bar follows the draft. Blocked by: Task 1 (uses `GoalPreview`/`goalCtx`).
1. RED `page-portfolio.test.js`: edit branch contains `<span>Goal name</span>` and renders `GoalPreview` (or the bar from the draft) — assert `editing` branch references `goalCtx`.
2. GREEN: `GoalRow` edit branch → `.pf-goal-card editing` holds a `.pf-add-grid` of captioned fields (name, target amount / target %, date) + `GoalPreview` for the draft (kind + fixed fields from the saved goal) + Save/Cancel in `.pf-add-actions`. `GoalRow` receives `goalCtx`. Bump page-goals to v3 only if Task 1 already shipped (otherwise stays v2).
3. Gates as Task 1. Commit `feat(goals): labelled edit mode with live progress bar`.

### Task 3 — UI feedback loop + evidence
1. Throwaway account seeded through the API (assets across ≥2 classes, one debt); screenshots: `goal-form-networth.png` (empty + typed target), `goal-form-debt.png`, `goal-form-allocation.png`, `goal-edit.png`. 2–3 look-adjust rounds expected.
2. Cleanup row: delete the seeded goals/assets/debt via API; close the row.

## Testing Strategy
- JS: `for f in dashboard/app/*.test.js; do node --test "$f"; done` (data suite also under `TZ=America/New_York` — unchanged here but run for the record).
- Syntax: esbuild over all JSX.
- Python fast loop not affected (no backend change) — run once at the end as regression evidence: `uv run pytest tests/integration tests/unit tests/test_*.py -q`.

## Risks & Mitigations
- **Riskiest: grid columns** — the goal form has 3–5 fields depending on kind while `.pf-add-grid` fixes 5 columns; mitigate with a `.pf-goal-form` modifier using `repeat(auto-fit, minmax(160px, 1fr))` so any field count lays out.
- **Preview for debt drafts** — `computeGoalProgress` needs `baseline`; the draft sets it from the chosen debt so it reads 0% rather than NaN.
- **Static-file freshness** — server serves `dashboard/` from disk; no restart needed, but cache-busters must bump or the browser keeps v1.

## Success Criteria
- [ ] AC1–AC8 demonstrated (tests + screenshots)
- [ ] All JS tests green, esbuild clean, Python fast loop unchanged
- [ ] Tri-axis review + fix-pass verification recorded
- [ ] Seeded demo data cleaned up

## Progress Log
| Date | Task | Status | Notes |
|---|---|---|---|
| 2026-08-26 | Phase 0–2 | Done | intent.md confirmed; spec.md saved |
| 2026-08-26 | Interrogation pass | Done | 3 findings fixed: (1) `.pf-add-grid` hard-codes 5 columns — modifier with auto-fit added to Task 1 + risk; (2) debt draft needs `baseline` for the helper — stated in Task 1; (3) cache-buster numbering across Tasks 1–2 clarified (v2 then v3). |
| 2026-08-26 | Task 1 | Done | labelled form + GoalPreview; efa800c |
| 2026-08-26 | Task 2 | Done | labelled edit mode, live bar; 90c86aa |
| 2026-08-26 | Task 3 | Done | UI loop, 1 look-adjust round; 52d9ca3 |
| 2026-08-26 | Tri-axis review (Opus 5; session authored on Fable 5) | Done | Standards Warn / Spec Warn / Simplicity Warn — no CRITICAL/HIGH; see Evidence |
| 2026-08-26 | Fix pass | Done | 11 findings fixed; f79af88 |
| 2026-08-26 | cleanup | Open | demo user goalform-demo@local.test seeded (3 assets, 1 debt, 3 goals, 1 suggestions cache doc) |

## Evidence

### Task 1 — labelled add form + preview
- RED: new test `goal form uses the labelled add-grid idiom…` failed on `function GoalPreview`; pre-existing test `goal progress … not inline math` asserted `page-goals.jsx` never calls `computeGoalProgress` — tightened to exactly one call (the draft preview; saved rows still use `resultsById`).
- GREEN: `GoalPreview` (draft → `computeGoalProgress(goal, goalCtx)`; debt draft takes today's balance as baseline), `GoalForm` on `.pf-add-row pf-goal-form` / `.pf-add-grid` with `<label><span>` captions, `.pf-add-actions`; `GoalsCard`/`PortfolioPage` pass `goalCtx`; CSS `.pf-goal-form` (border + auto-fit grid), `.pf-goal-preview`; cache-busters page-goals v2, page-portfolio v15, styles v13 (final tree after look-adjust 52d9ca3: page-goals v4, styles v15; after fix pass: page-goals v5, styles v16).
- Gates: JS 4/29/5/22/1 pass (data also `TZ=America/New_York` 29); esbuild 0 errors.

### Task 2 — labelled edit mode
- RED: `goal edit mode uses labelled fields…` failed on `pf-add-grid` in the edit branch.
- GREEN: edit branch → `.pf-add-grid` captioned name / target / date, `<GoalPreview draft={{ ...goal, ...draft }}>` (preview keeps a saved `baseline`, so an edited debt goal does not reset to 0%), Save/Cancel in `.pf-add-actions`; `.pf-goal-card.editing` spans the grid row on paper-2. Cache-busters page-goals v3, styles v14.
- Gates: JS all green (23 portfolio), esbuild 0 errors.

### Task 3 — UI feedback loop
- Server `uvicorn webapp.api:app` on :8501 serves `dashboard/` from disk — no backend change, no restart needed; cache-busters bumped.
- Demo user `goalform-demo@local.test` (login without password = demo mode) seeded via API: cash 42k, equities 118k, retirement 65k, Car loan 18.5k, goals: net worth 250k (2027-12-31), pay off Car loan (2027-06-30), equities at 60%. Opening the page also triggered one live AI-suggestions generation (cache doc to delete).
- Screenshots (in this folder): `goal-form-networth-empty.png` (captions, muted "Enter a target", "Net worth today 206,500.00"), `goal-form-networth.png` (300k → 69%, "206,500.00 of 300,000.00 · by 2028-06-30"), `goal-form-debt.png` ("18,500.00 left of 18,500.00 · baseline set when you save", 0%), `goal-form-allocation.png` (equities 52.4% vs 30% → 25%), `goal-edit.png` (Quarter million edited to 200k → "Reached", green bar; Cancel restored 83%). Preview at target 52% read "Reached" (inside ±2 pp band).
- Look-adjust round 1: "Enter a target" in the accent serif slot was too loud → `.muted` variant (52d9ca3). Console: no errors (Babel dev warning only).
- Regression: `uv run pytest tests/integration tests/unit tests/test_*.py -q` → **197 passed**.

### Tri-axis review (Opus 5)
- **Standards: Warn** — MEDIUM: preview duplicates the saved-card markup and already drifted ("Reached" vs "Done ✓"); visible `<label>` text vs stale `aria-label` mismatch (WCAG 2.5.3); `GoalForm` 96 lines; `net`/`debtsById` props duplicate `goalCtx`; preview branch logic only source-shape tested. Nits: "baseline set when you save" reachable in edit mode for a legacy debt goal with null baseline; duplicated CSS rule; tests pin version floor / CSS keyword; redundant assertion; `pct`/`goal` name collisions. Security clean (JSX text nodes, clamped width).
- **Spec: Warn** — Stories 1–3 Met; AC1–AC8 Met (AC8 by construction). Out-of-scope clean; payloads byte-identical to `main`. MEDIUM: `plan.md` duplicated/corrupted by an earlier edit; demo data not yet cleaned; cache-buster evidence stale (v4/v15 shipped vs v2/v3 recorded); net-worth preview text bypasses `goalTargetText`. LOW: optional name field for debt/allocation not in the task list and name carried across kind switches ("Three hundred" debt goal). Nits: empty-target bar at 0% vs intent's "at current value"; edit Save enabled with cleared target; AC8 undemonstrated; error hint relocated; Save promoted to primary / order swapped.
- **Simplicity: Warn** — MEDIUM: Goal name field written three times; `net`/`debtsById` redundant with `goalCtx`; duplicated / inert CSS. Nits: 5-arm nested ternary; `Field` one-liner option; tests pin copy strings and a call count.

### Fix pass (f79af88)
- Fixed: single Goal name label with per-kind placeholder (`GOAL_NAME_PLACEHOLDER`); `setName("")` on kind change; redundant `aria-label`s removed (only "Goal kind" remains, text matches); preview shows "Done" + check like the saved card; "baseline set when you save" gated on `isNew = draft.id == null`; edit Save disabled when the target is cleared; `net`/`debtsById` props dropped — `GoalsCard` forwards `goalCtx.net`/`goalCtx.debtsById`; CSS merged into one grid selector, inert preview background removed; `emptyText` lookup + `targetText` replace the nested ternary; `pctLabel`/`previewGoal` names; tests: redundant assertion dropped, version check = "not v=1", CSS check = selector presence. `plan.md` de-duplicated; cache-buster evidence corrected. `GoalForm` 96 → 83 lines.
- **Declined (recorded):** `GoalCardShell` extraction (two call sites; saved card carries tools + projection line — a 10-prop component is longer than the duplication); moving preview derivation into `data.js` with executed tests (JSX layer is source-shape tested by repo convention, math stays in the unit-tested `computeGoalProgress`) — **follow-up** if the preview grows; splitting `GoalForm` further (83 lines of mutually exclusive JSX branches); net-worth preview text "current of target" vs saved card's target-only text (deliberate — the preview's job is current-vs-target; today's value lives in the hero); empty-target bar at 0% (no denominator to place "current" on); Save primary + Cancel-then-Save order (matches the Assets form actions row); error hint above the form (keeps the band flush).
- Departures from the plan now recorded: optional Goal name for debt/allocation kinds (backend default name still applies when blank); cache-busters page-goals v5 / styles v16 / page-portfolio v15.
- UI re-verified after the fix: `goal-form-networth.png` (69%, "206,500.00 of 300,000.00"), `goal-form-allocation.png` (52% → "Done"), `goal-edit.png` (200k → "✓ Done", green bar; empty target → Save disabled + "Enter a target"; Cancel restores 83%); name cleared on kind switch (js check). Console: 0 errors.
- Gates after fix: JS 4/29/5/23/1 pass; esbuild 0 errors.
