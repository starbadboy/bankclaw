# Goal form redesign — labelled fields + live progress preview — Implementation Plan

> **For Agent:** Execute task-by-task; verify before proceeding; commit after each task.
> **TDD Rule:** No production code without a failing test first.

**Goal:** Add form + Edit mode on the Goals page adopt the Assets-tab labelled form idiom, with a live mini-card preview of the draft goal computed from today's portfolio.
**Architecture:** UI-only change in `dashboard/app/page-goals.jsx` — `GoalForm` rebuilt on `.pf-add-row`/`.pf-add-grid`; a small `GoalPreview` renders `computeGoalProgress(draft, goalCtx)` with the existing bar/target-text pieces; `GoalRow`'s edit branch reuses the same labelled fields and preview. `GoalsCard` passes `goalCtx` (already computed in `PortfolioPage`) down. Small CSS block in `styles.css`; cache-busters in `index.html`.
**Complexity Path:** Simplified TDD — no browser E2E harness in this repo (`tests/e2e` is Streamlit-mocked).
**Status:** In progress
**Branch:** `feat/goal-form-redesign`

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

## Evidence
