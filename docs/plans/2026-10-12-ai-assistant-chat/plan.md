# AI Assistant Chat — Implementation Plan

> **For Agent:** Execute task-by-task; verify before proceeding; commit after each task.
> **TDD Rule:** No production code without a failing test first.

**Goal:** An Assistant page where the user chats in saved threads. DeepSeek answers by calling read-only, user-scoped tools over transactions and the portfolio (see `intent.md`, `spec.md`).
**Architecture:** New `webapp/assistant.py` (tools → chat loop → thread store on Mongo `assistant_threads`) behind 4 routes in `webapp/api.py` → `dashboard/app/api.js` client → new `dashboard/app/page-assistant.jsx`, wired into `shell.jsx` nav and routing.
**Complexity Path:** `Simplified TDD path`. The browser harness in `tests/e2e` is opt-in and runs with Mongo disabled and no LLM stub, so the assistant can't run there without new fake infrastructure. A real-browser UI loop on a throwaway account covers end-to-end.
**Status:** Complete

## Architecture Review
Files that change:
- `webapp/api.py` — extract `_portfolio_snapshot(user)` (prefactor); 4 assistant routes
- `webapp/assistant.py` — **new**: tools, `run_turn`, thread store, exceptions
- `dashboard/app/api.js` — `apiAssistantSend`, `apiAssistantThreads`, `apiAssistantThread`, `apiAssistantDelete`
- `dashboard/app/page-assistant.jsx` — **new**: `AssistantPage`
- `dashboard/app/shell.jsx` — nav item in both modes; mode-independent route; `onMode` keeps `assistant`
- `dashboard/index.html` — one `<script>` tag (cache-busting is automatic: `?v=__V__`)
- `dashboard/app/styles.css` — chat layout block
- Tests: `tests/unit/test_assistant.py` (new), `tests/test_assistant_api.py` (new), `tests/test_portfolio_api.py` (prefactor stays green), `dashboard/app/page-assistant.render.test.js` (new)

Reused: `get_transactions_by_date_range`, `ensure_main_profile` and the main-profile filter rule; `list_portfolio`/`list_valuations`/`list_goals`/`list_asset_types`; `goal_advisor.build_goal_aggregate`; `deepseek_config`; the goal advisor's lazy-OpenAI + timeout + own-exception pattern; `_current_user`; `_fetch`; the `_JsonRequest` and MagicMock-Mongo test helpers; the goals render-probe pattern.

## Shape — Ladder Pass
| Candidate | Rung reached | Kept / Skipped | Reason (one line) |
|---|---|---|---|
| Portfolio snapshot for the assistant | 2 | Kept (prefactor) | Same closure already in the goal-suggestions route; extract, don't copy |
| Portfolio aggregate | 2 | Kept | `build_goal_aggregate` reused; only goal name/target/date added alongside |
| Transaction fetch | 2 | Kept | `get_transactions_by_date_range` + `df.to_dict("records")`; aggregation in plain Python so tests need no pandas |
| Merchant key | 7 | Kept (copied rule) | Same "first 4 words, upper" rule as ai_coach, re-implemented in a few lines — ai_coach's is inline and imports pandas/openai at module load |
| LLM client / tool calling | 5 | Kept | Installed `openai` client, `tools=` param; no agent framework |
| Thread store | 7 | Kept | One small set of functions on one collection; no repository class |
| Separate thread-repository module | 1 | Skipped | Lives in `assistant.py`; `skipped: split file, add when assistant.py passes ~400 lines` |
| Streaming | 1 | Skipped | Intent: out of scope |
| Markdown rendering | 4 | Skipped | `white-space: pre-wrap` + prompt asks for plain bullets; `skipped: markdown, add when replies need tables/links` |
| Thread rename / pagination | 1 | Skipped | Out of scope; list capped at 50 newest; `add pagination when users exceed 50 threads` |
| Concurrency lock (like goal advisor) | 1 | Skipped | Chat turns are short and per-user; `add when DeepSeek rate-limits concurrent users` |
| Privacy-mode masking of replies | 1 | Skipped | `add when users ask for blur in chat` (spec Further Notes) |
| Horizontal vs vertical | — | Vertical | T1 is a full tracer bullet (route → loop → store → page) |

## Implementation Steps

### T0 — Prefactor: shared portfolio snapshot (behaviour-neutral)
- Move the `build_portfolio` closure in `get_goal_suggestions` (`webapp/api.py`) to module-level `_portfolio_snapshot(user) -> dict`; the route passes `lambda: _portfolio_snapshot(user)`.
- Verify: `uv run pytest tests/test_portfolio_api.py tests/unit/test_goal_advisor.py` green, unchanged tests.
- Blocked by: none.

### T1 — Tracer: ask one question, get an answer, saved in a thread
Delivers: AC1, AC6, AC8 (cash_flow only), AC9 (length), basic AC10, AC11, on one thread.
- `assistant.py`: `AssistantError` base; `AssistantNotConfigured`, `AssistantInputError`, `ThreadNotFound`. Sign convention as in ai_coach: amount < 0 is spend, > 0 is income. `cash_flow_summary(records, **args)` — tool args `start`/`end` must be ISO dates (default: last 90 days), invalid → error object to the model; `run_turn(client, history, message, tool_ctx) -> str` (≤5 tool calls, then `tool_choice="none"`), `send_message(user, profile_id, thread_id, message, load_records, load_portfolio, client=None) -> {thread, reply}` where `load_records(start, end, profile_id)` fetches per tool call. For an existing thread the **stored** `profile_id` is used and the request's is ignored (AC6); the request's `profile_id` is stored only when creating a thread, thread store `_create/_append/_get` with every query filtered by `user_email`. `_ensure_indexes` on `[("user_email",1),("updated_at",-1)]`.
- `api.py`: `POST /api/assistant/messages`. Validates message is a str of 1..2000 chars after strip and ids are str ≤64. `load_records` wraps `get_transactions_by_date_range` with the same main-profile rule as `get_transactions` (`all`/empty → no filter). Runs `send_message` in `asyncio.to_thread`. Maps NotConfigured→503, InputError→400, ThreadNotFound→404, other→502 with a logged warning; `_MONGO` false → 503.
- Frontend: `apiAssistantSend`; `AssistantPage` with conversation + composer, thinking indicator, error banner that keeps the input text; nav item "Assistant" (icon `sparkle`) in `ledgerItems` only for now; route `page === "assistant"`.
- Tests: `tests/unit/test_assistant.py` (cash_flow totals/grouping; run_turn with fake client: dispatches a tool, caps at 5, history cap 20, unknown tool → error object; send_message writes only on success, all queries carry user). `tests/test_assistant_api.py` (400 on >2000 chars, 503/404/502 mapping, user/profile passed). `page-assistant.render.test.js` (empty, with messages, thinking, error).
- Blocked by: T0.

### T2 — Remaining tools
Delivers: AC2, AC8 fully.
- `find_transactions` (filters, count/total over all matches, ≤20 rows, whitelist of 4 fields, sort date|amount) and `portfolio_summary` (`build_goal_aggregate` on `_portfolio_snapshot` + goals' name/kind/target/target_date). Register both in the tool schema; `load_portfolio` is called lazily, only when the tool is used.
- Tests: row cap, field whitelist (no `user_email`, `bank`, `profile_id`, `_id`), totals over >20 matches, portfolio tool output shape.
- Blocked by: T1.

### T3 — Thread list, open, delete
Delivers: AC3 (reload), AC4, AC5, AC7.
- `assistant.py`: `list_threads(user)` (≤50, newest first, id/title/updated_at), `get_thread(user, id)`, `delete_thread(user, id)`; invalid ObjectId → `ThreadNotFound`.
- `api.py`: `GET /api/assistant/threads` (returns `{threads, configured}`, `configured` = `DEEPSEEK_API_KEY` set, so the page can show "not configured" before any send), `GET /api/assistant/threads/{id}`, `DELETE /api/assistant/threads/{id}`.
- Frontend: thread list column (New chat, titles, delete with confirm), open thread loads messages; after a send, the list refreshes and the new thread is selected.
- Tests: user scoping on list/get/delete, foreign id → 404, render probe with a thread list.
- Blocked by: T1 (shares `assistant.py`/`api.py` with T2 → run T2 and T3 sequentially).

### T4 — Both modes, degraded states, styling
Delivers: AC10 (page-level 503 messages), nav in Portfolio mode, AC11 polish.
- `shell.jsx`: add the item to `portfolioItems`; render `AssistantPage` when `page === "assistant"` regardless of mode; `onMode` leaves `assistant` untouched.
- Page: `configured: false` shows "AI assistant not configured" and disables the composer; a 503 on the thread list shows "Database unavailable"; example prompts in the empty state; mobile layout (thread list collapses above the conversation under the existing 720px breakpoint).
- `styles.css` chat block using existing tokens.
- Tests: render probe for not-configured state.
- Blocked by: T3.

## Testing Strategy
- Fast loop: `uv run pytest tests/integration tests/unit tests/test_*.py` (the full `pytest .` exceeds 2 min — CLAUDE.md).
- JS: `for f in dashboard/app/*.test.js; do node --test "$f"; done` + `npx esbuild dashboard/app/*.jsx --loader:.jsx=jsx --outdir=/tmp/jsxcheck` at every GREEN.
- Lint: `uv run ruff check webapp tests`.
- UI loop (T1, T3, T4): restart uvicorn after backend edits. Use a throwaway account with data seeded via the API, then exercise every view and state: empty, thread with messages, thinking, error, not-configured, thread list, delete, Portfolio mode, mobile width. Screenshot each. Time one real DeepSeek turn.

## Risks & Mitigations
- **Riskiest: DeepSeek tool calling on `deepseek-v4-pro`.** Untested in this repo. Mitigation: T1's UI loop does one real call before T2. If tool calls fail, stop and report (fallback is a model env override via `DEEPSEEK_MODEL`).
- **Latency:** tool rounds × ~5–30 s each. Mitigation: timeout per call (120 s), 5-call cap, latency posted on the PR; streaming stays a follow-up.
- **Prompt injection via transaction descriptions:** descriptions reach the model. Impact is bounded because tools are read-only and scoped to the user's own data; nothing can write or reach other users.
- **Ordering-sensitive suite:** new route test stubs pandas like `test_portfolio_api.py`; `assistant.py` must not import pandas/openai at module import.

## Success Criteria
- [x] AC1–AC11 met (spec.md)
- [x] Fast pytest loop, JS tests, esbuild green; ruff adds no new rule families beyond the sibling AI modules' house style
- [x] Screenshots of every view/state on the PR, plus measured latency
- [x] Tri-axis review + fix-pass verdict on the PR

## Record
- **Branch:** `feat/ai-assistant-chat`
- **PR:** https://github.com/starbadboy/bankclaw/pull/5
- **Departures:**
  - Merchant key drops words containing digits after the first word (ai_coach's plain "first 4 words" split `GRAB FOOD SINGAPORE A1/B2/C3` into separate merchants in the T1 UI loop) — ladder row "Merchant key" is now a variant, not a copy
  - Replies have `**` stripped and the prompt bans bold — DeepSeek used markdown bold despite "plain text", which renders literally in the pre-wrap bubble
  - Ledger tools exclude category `Transfer` unless a category is asked for — matches the dashboard (`data.js` spend excludes transfers), so AC1 totals agree
  - Assistant tool-call messages echo DeepSeek `reasoning_content` within a turn — required by DeepSeek thinking mode for multi-round tool calls
  - Thread title is cut at 59 characters + "…" (spec: "trimmed to 60") — the ellipsis counts toward the 60
  - JS client tests live in `dashboard/app/api.test.js` (not listed in the plan's file list)
  - Review fixes: shared `_load_records(user, start, end, profile_id)` in `api.py` (assistant uses it; the two older inline copies are left as they were); records cleaned of NaN before tools; non-finite tool numbers rejected; empty reply → 502, nothing saved; thread capped at 200 messages ("start a new chat"); thread index created once per process
- **Declined findings:**
  - Reply lost when the save fails after a successful LLM call (Standards LOW) — rare; returning an unsaved reply changes the API contract. The draft is restored so the user can retry
  - Disable the composer when the thread list returns 503 (Spec LOW) — within spec; a failed send restores the draft
  - Replace the `SimpleNamespace` ctx with two arguments (Simplicity nit) — churns the test helpers for no behaviour gain
  - Delete the `is_configured` test (Simplicity nit) — a cheap check of the `configured` contract the page depends on
  - Hoist `ensure_main_profile` out of the per-tool-call loader (Standards nit) — at most 5 cheap lookups per turn; blocking I/O must stay off the event loop
- **Follow-ups:** privacy-mode masking in chat; streaming; markdown rendering; switch `get_transactions` / `ai_review` to `_load_records`; existing `/api/transactions` and `/api/categories` return 500 (not 503) when Mongo is unreachable
- Review: tri-axis on claude-sonnet-5-5 (no CRITICAL/HIGH); fix pass `Verdict: Clean with nits`
- Interrogation pass: 5 findings fixed (thread-fixed profile vs request profile ambiguity; `load_records` signature/date args; key-missing undetectable before first send → `configured` flag; merchant-key "reuse" was really a copy; breakpoint aligned to existing 720px)
