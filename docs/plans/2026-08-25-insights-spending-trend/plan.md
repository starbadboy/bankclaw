# Insights Spending Trend Implementation Plan

> **For Agent:** Execute task-by-task; verify before proceeding; commit after each task.
> **TDD Rule:** No production code without a failing test first.

**Goal:** Spending-trend view in the Cash flow panel — cumulative day-by-day spend line per month in the selected range.
**Architecture:** One pure function in the data module computes per-month cumulative series from already-loaded transactions; the Insights page gains a pill toggle and a trend chart following the existing multi-line SVG idiom. No API/DB changes.
**Complexity Path:** pending user choice
**Status:** Draft

## Architecture Review
- Reuse: `insightsFilter` (range window), `excludedCats` set + the exclusion rule from the months memo (`t.amount < 0 && excludedCats.has(t.category)`), `CategoryTrendChart`'s SVG/hover/tooltip idiom, `fmtSGD` + privacy, `seg` pill idiom.
- Data source: `filtered` transactions already in the page; trend needs its own month window (range months up to and including current month) — note the existing `months` memo derives buckets only from transactions present, while AC6 requires zero-spend months to appear: the helper must enumerate the window's months, not discover them.
- Exact files: `dashboard/app/data.js`, `dashboard/app/data.test.js`, `dashboard/app/page-insights.jsx`, `dashboard/app/page-insights.test.js`.

## Shape — Ladder Pass

| Candidate | Rung reached | Kept / Skipped | Reason (one line) |
|---|---|---|---|
| `computeSpendingTrend` in data module | 2→7 | Kept | New math; reuses date idioms; single test point |
| Toggle + `SpendingTrendChart` in insights page | 2→7 | Kept | `seg` pills + CategoryTrendChart idiom reused |
| New chart library | 1 | **Skipped** | skipped: existing SVG idiom covers it; add never |
| Month picker | 1 | **Skipped** | skipped: out of scope per intent; add when users ask |
| Normalizing month lengths (spend/day rate) | 1 | **Skipped** | skipped: honest raw cumulative per spec; add when comparison fairness complaints arrive |
| Server-side aggregation | 1 | **Skipped** | skipped: transactions already client-side |

**Prefactoring check:** none needed — the toggle drops into the panel header and the chart into the panel body without untangling anything. (Checked, not skipped silently.)

**Slicing:** vertical. Task 1 is a tracer: helper (full math, TDD) + toggle + line rendering, demoable end-to-end. Task 2 adds hover tooltip + end marker + legend polish on the working slice. Not horizontal — the UI appears in task 1, per the flow's own rule.

**Session split:** both tasks fit one session. Edges: Task 1 → Task 2 → Verify.

## Implementation Steps

### Task 1: Tracer — helper + toggle + lines (demoable)
**Files:** `dashboard/app/data.js`, `dashboard/app/data.test.js`, `dashboard/app/page-insights.jsx`, `dashboard/app/page-insights.test.js`
**RED:** behavioral tests for `computeSpendingTrend(transactions, { rangeMonths, excludedCategories, now })` → `[{ key, label, cumulative: [...], isCurrent }]`: exclusion filtering, income ignored, partial current month cut at now, zero-spend month emits zeros, leap February (now = 2024-02-29), 31-day month, window membership incl. current month. Plus source assertions: trend pill, helper call in page.
**GREEN:** implement helper — window = current month + preceding months, `max(2, rangeMonths)` total, where `rangeMonths` is the numeric prefix of the range id (`"3m"` → 3; parse once at the call site); enumerate those months (AC6: enumerate, don't discover), bucket money-out per day, cumulative sum, cut current at now; `trendView` state + `seg` toggle `[Cash flow | Spending trend]`; `SpendingTrendChart` rendering one path per month (newest solid `var(--debit)`, older dashed faded), zero baseline for empty months.
**Verify:** `node --test dashboard/app/data.test.js dashboard/app/page-insights.test.js`; esbuild JSX syntax gate; demoable in app.
**COMMIT:** `feat(insights): spending trend view with per-month cumulative lines`

### Task 2: Hover tooltip + end marker + polish
**Files:** `dashboard/app/page-insights.jsx`, `dashboard/app/page-insights.test.js`
**RED:** source assertions: hover state, per-month cumulative in tooltip, end marker on current month, privacy blur on tooltip values.
**GREEN:** hover index per CategoryTrendChart idiom; tooltip lists each month's total at hovered day (skip months shorter than hovered day); circle marker at current line end; legend line.
**Verify:** both test files; esbuild; screenshots (UI feedback loop) of trend view at 1m and 6m + hover.
**COMMIT:** `feat(insights): spending trend tooltip and month-progress marker`

## Testing Strategy
Test point 1 behavioral (data.test.js, boundary-heavy per the TDD boundary rule); test point 2 source assertions; esbuild syntax gate each GREEN; full JS sweep by exit code + non-e2e pytest untouched-backend proof at Verify; screenshot evidence per changed view.

## Risks & Mitigations
- **Risk:** day-of-month bucketing hits the same month-boundary class as the portfolio HIGH → Mitigation: leap/31-day fixtures in RED, not discovered at review.
- **Risk:** exclusion semantics drift from cash-flow bars → Mitigation: same predicate, asserted in tests.
- **Risk:** 6m = 6 overlaid lines gets visually noisy → Mitigation: fade older months progressively; screenshot round judges it.

## Success Criteria
- [ ] AC1–AC6 met
- [ ] All JS suites pass; esbuild clean; pytest untouched-backend proof
- [ ] Screenshots of each changed view in Progress Log
- [ ] Tri-axis review run, findings recorded
- [ ] Evidence before Complete

## Progress Log
| Date | Task | Status | Notes |
|---|---|---|---|
| 2026-08-25 | Folder authored | Done | Grilling (2 frontier rounds), test-point gate, spec confirmed |
| 2026-08-25 | Interrogation pass: 2 findings fixed | Done | Window-count rule made explicit (max(2,N) incl. current); rangeMonths derivation stated |
