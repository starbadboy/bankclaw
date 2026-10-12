# Intent — AI Assistant Chat

## 0. Intent
- **Problem:** Users can see their ledger and wealth data on fixed dashboard pages, and the existing AI features (spending review, goal suggestions) only give fixed one-shot outputs. There is no way to ask a free-form question ("how much did I spend on Grab in March?", "can I hit my net-worth goal at my current savings rate?") and get an answer, or suggestions, grounded in the user's own data.
- **Proposed outcome:** A new **Assistant** page in the dashboard sidebar. The signed-in user chats in saved threads. Each reply comes from DeepSeek, which calls read-only server-side query tools over that user's transactions and portfolio. The reply quotes server-computed numbers and gives practical suggestions.
- **Affected systems:** FastAPI backend (`webapp/api.py` plus a new assistant module), MongoDB (one new collection for threads), React dashboard (new page, nav item, API client).
- **Constraints:**
  - LLM: DeepSeek via the existing OpenAI client and `deepseek_config` (no new provider or dependency).
  - Privacy: the LLM never receives the full transaction list. Tools return server-computed totals and at most 20 example rows per call, with only date, description, amount and category. No account numbers, emails or profile names. This relaxes the "aggregates only" rule from `ai_coach`, deliberately and within these limits.
  - Guards: user message ≤ 2000 characters; ≤ 5 tool calls per reply; only the last ~20 messages of a thread go to the model; no daily cap.
  - Blocking LLM and DB I/O runs off the event loop (`asyncio.to_thread`) and has a timeout.
  - Errors: the module defines its own exception types for clean 503 (not configured or DB unavailable) and 502 (LLM failure) responses. It does not catch stdlib exceptions broadly.
- **Resolved decisions:**
  - Data access → LLM tool calling over server-side query functions
  - Data scope → Ledger (transactions, categories) + Wealth (assets, debts, net worth, goals)
  - UI surface → new "Assistant" sidebar page in the React dashboard
  - History → saved per user in Mongo, multiple threads (new chat, list titled by first question, delete). **New Mongo collection: approved as a DB change by choosing this option.**
  - Actions → read-only. Suggestions are text only; no write tools
  - Delivery → one complete reply per request with a "thinking…" indicator; no streaming. The real latency is timed and posted as evidence
  - Limits → length, tool-call and context guards; no daily cap
  - Profile → ledger tools use the dashboard's selected profile (or All), fixed per thread at creation; portfolio is per user
  - Example rows → ≤ 20 per tool call, with only date, description, amount and category
  - Degraded mode → nav item always shown; the page shows a clear "not configured / database unavailable" message (503)
- **Assumptions (confirm at gate):**
  - The assistant replies in the language the user writes in
  - Existing AI review, goal suggestions and the Streamlit app are unchanged
  - Only the signed-in user's own data is reachable. Every tool and thread query is filtered by the authenticated email
- **Out of scope:** streaming responses; write or one-click actions; Streamlit UI; a floating chat panel; daily message caps or billing; sending raw transaction lists; cross-user or shared threads; voice or file upload in chat; renaming threads.
- **Open questions:** none.

**Done looks like:** On a throwaway account with seeded data, the user opens Assistant, asks "How much did I spend on food last month?", and gets an answer whose number matches the dashboard. They ask a follow-up in the same thread and get a context-aware reply. They reload the page and the thread is still there. They delete it and it's gone. Removing the API key shows the not-configured message.
