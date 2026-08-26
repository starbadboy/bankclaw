# Goal form redesign — labelled fields + live progress preview — Intent

## 0. Intent
- **Problem:** The add-goal form on the Goals page is still a bare inline row (unlabelled `select`/inputs, placeholder-only, shrink-wrapped date). It never adopted the labelled form idiom the Assets tab uses, so it looks unfinished next to the redesigned hero and cards. The inline Edit mode on goal cards has the same problem. Neither tells the user where they stand today while they type a target.
- **Proposed outcome:** Add form and Edit mode use the existing labelled form style (uppercase captions, paper-2 band, actions row). As the user types a target, a mini goal card underneath shows the same bar + % + "current vs target" text the saved cards show, computed from today's portfolio. Saving still creates the same goal payloads as before.
- **Affected systems:** `dashboard/app/page-goals.jsx` (`GoalForm`, `GoalRow` edit branch, one shared preview piece), `dashboard/app/styles.css` (small goal-form block reusing `.pf-add-grid` rules), `dashboard/index.html` cache-busters, `dashboard/app/page-portfolio.test.js` (or a `page-goals.test.js`).
- **Constraints:**
  - UI only — no API, repository or `data.js` progress/projection changes; goal payloads sent on create/update are unchanged.
  - Progress semantics unchanged: net worth = net ÷ target; debt payoff = paid ÷ baseline (baseline captured on save, so the preview reads 0% with the current balance shown); allocation = closeness to the ±2 pp band. All from live `goalCtx` — nothing is snapshotted for net-worth goals.
  - Reuse `computeGoalProgress` and the existing card pieces for the preview; no new CSS system, no new dependencies.
  - Same editorial idiom as the rest of the portfolio pages.
- **Resolved decisions:**
  - Form style → reuse the Assets-tab labelled form idiom (`.pf-add-row` / `.pf-add-grid`), inline below the cards (not collapsed behind a button)
  - Live context → a **mini goal card preview** (bar + % + current-vs-target text) under the fields, recomputed from the draft on every keystroke; empty target → bar at current value with a prompt to enter a target
  - Projection in the preview → **no**; projection appears on the card after save
  - Edit mode → same labelled style, and the card's bar updates live from the draft target
  - Net-worth progress baseline → **keep net ÷ target** (no baseline field)
- **Out of scope:**
  - Storing a net-worth baseline / growth-since-set progress
  - Collapsible or modal form; multi-step wizard
  - Projection/ETA inside the form
  - Changes to hero, suggestions panel, sorting, or goal semantics
- **Open questions:** none.
