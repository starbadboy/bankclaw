# Portfolio goals — richer kinds, projections, AI suggestions — Intent

## 0. Intent
- **Problem:** Goals today are a single kind (net-worth milestone) with a name, amount and optional date, rendered as a bare progress bar. They answer "how far to X" but not "when will I get there", "should I pay this debt first", or "what should I even aim for". The Goals page looks unfinished next to the rest of the portfolio UI.
- **Proposed outcome:** The Goals page becomes a complete view: a summary hero (next milestone, its projected date, goals done/total), goal cards for **three kinds** — net-worth milestone, debt payoff, asset-class allocation — each with progress plus an on-track projection derived from valuation history, and an **AI suggestions** panel that proposes 3–5 fully specified goals from portfolio aggregates, each addable in one click. The Net worth hero gains one line naming the nearest goal and its ETA.
- **Affected systems:** `webapp/portfolio_repository.py` (goal fields), `webapp/api.py` (goal payloads; new suggestions route), new `webapp/goal_advisor.py` (aggregates → DeepSeek → structured suggestions, Mongo-cached), `dashboard/app/data.js` (progress + projection helpers), `dashboard/app/page-portfolio.jsx` (Goals page, GoalsCard, Net worth hero line), `dashboard/app/api.js`, `dashboard/app/styles.css`, tests in `tests/` and `dashboard/app/*.test.js`.
- **Constraints:**
  - Existing net-worth goals keep working unchanged: documents without `kind` are treated as `net_worth`; API stays backward compatible.
  - AI sees **aggregates only** (net worth, per-class allocation %, each debt's balance + APR, 12-month net-worth trend, existing goals) — never holding names, tickers or transactions. Same DeepSeek client/config and Mongo-cache pattern as AI Coach; when `DEEPSEEK_API_KEY` is unset the panel says so and the rest of the page works.
  - Projections are deterministic from valuation history (no AI), explainable in one sentence, and say "not enough history" rather than guessing.
  - Schema: **additive fields** on `portfolio_goals` (`kind`, `debt_id`, `baseline`, `asset_kind`, `target_pct`) and one new cache collection `ai_goal_suggestions`. No migration; MongoDB is schemaless. Flagged here because the flow's DB-change gate applies — confirming this Intent confirms these.
  - Dates handled as ISO strings; JS date tests also run under `TZ=America/New_York` (CLAUDE.md lesson).
- **Resolved decisions:**
  - Goal kinds → **net worth, debt payoff, asset-class allocation**
  - Debt payoff progress → **baseline = debt balance at goal creation**; done at 0; if the debt is deleted the card says so and offers removal
  - Allocation goal → **target % of total assets with a ±2 pp band, no direction**; progress = closeness to the band; class with no assets = 0%
  - Projection → **linear trend over the last 12 months of net-worth valuations** (debt goals: that debt's own history); needs ≥2 points ≥30 days apart; shows projected completion date when the trend reaches the target, and "need +S$X/month" when a target date is set; allocation goals get no projection
  - AI → **aggregates only → 3–5 ready-to-add goals** (kind, target, date, rationale, priority); **Accept** creates the goal immediately; **Dismiss** hides it (persisted in the cache doc)
  - AI refresh → **cached per user, manual Refresh, stale hint** when net worth or goal count differs from the snapshot; first visit generates once if the key is set
  - Placement → **Goals page redesign + one "next milestone" line on the Net worth hero**; nearest goal = highest progress among unfinished goals
  - Visual style → same editorial idiom as the Net worth hero and panels (no new design system)
- **Out of scope:**
  - Goal history charts / progress over time
  - Notifications, celebrations, archiving of done goals (done goals stay listed with "Done" and can be removed)
  - Manual ordering of goals (sorted: unfinished by progress desc, then done)
  - AI editing or deleting existing goals; AI suggestions inside the AI Coach page
  - Per-holding goals ("ADSK to S$X"), savings-rate goals, contribution tracking
  - FX / multi-currency (S$ throughout)
- **Open questions:** none.
