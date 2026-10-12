"""AI Assistant — free-form chat over the user's own data via read-only tools.

Mirrors ``goal_advisor``: DeepSeek via the OpenAI client (imported lazily), own
exception types for the route to map. The model never sees the transaction list:
tools compute totals server-side and return at most a few whitelisted rows.
Threads live in Mongo ``assistant_threads``; a turn is saved only after a reply.
This module imports neither pandas nor openai at import time (route tests stub pandas).
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Callable

from bson import ObjectId
from bson.errors import InvalidId

from webapp.db import get_db
from webapp.deepseek_config import DEEPSEEK_BASE_URL, get_deepseek_model
from webapp.goal_advisor import build_goal_aggregate

_THREADS_COLLECTION = "assistant_threads"
MAX_MESSAGE_CHARS = 2000
_MAX_TOOL_CALLS = 5
_HISTORY_MESSAGES = 20
_MAX_GROUPS = 25
_TITLE_CHARS = 60
_DEFAULT_RANGE_DAYS = 90
_LLM_TIMEOUT_SECONDS = 120
_GROUP_BY = ("category", "merchant", "month")
_SORTS = ("date", "amount")
_MAX_ROWS = 20
_ROW_FIELDS = ("date", "description", "amount", "category")


class AssistantError(Exception):
    """Base for errors the API maps to a client-facing status."""


class AssistantNotConfigured(AssistantError):
    """DEEPSEEK_API_KEY is not set."""


class AssistantInputError(AssistantError):
    """The request (or a tool's arguments) is invalid."""


class ThreadNotFound(AssistantError):
    """No thread with that id belongs to this user."""


_SYSTEM_PROMPT = """You are Bankclaw's personal-finance assistant for a user in Singapore (currency SGD).
Today is {today}. Answer questions about the user's own transactions and portfolio and give practical suggestions.

Rules:
- Use the tools to look data up; never guess numbers. Quote the totals the tools return — do not re-add rows yourself.
- Spending amounts are positive numbers in tool results; transfers between own accounts are excluded unless asked for.
- You are read-only: you cannot change data. If the user wants a change, tell them where in the app to do it.
- If the data cannot answer the question, say so plainly.
- Reply in the language the user writes in. Plain text only: short paragraphs and "- " bullets; no markdown (no **bold**, tables or headings).
"""

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "cash_flow_summary",
            "description": "Income, spend and net totals for a date range, grouped by category, merchant or month. "
            "Optional filters: exact category, merchant/description substring.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "YYYY-MM-DD, inclusive. Default: 90 days ago."},
                    "end": {"type": "string", "description": "YYYY-MM-DD, inclusive. Default: today."},
                    "group_by": {"type": "string", "enum": list(_GROUP_BY)},
                    "category": {"type": "string"},
                    "merchant_contains": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_transactions",
            "description": "Individual transactions matching filters, for questions about specific purchases. "
            "match_count and totals cover every match; at most 20 example rows are returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "YYYY-MM-DD, inclusive. Default: 90 days ago."},
                    "end": {"type": "string", "description": "YYYY-MM-DD, inclusive. Default: today."},
                    "category": {"type": "string"},
                    "merchant_contains": {"type": "string"},
                    "min_amount": {"type": "number", "description": "Minimum absolute amount in SGD."},
                    "max_amount": {"type": "number", "description": "Maximum absolute amount in SGD."},
                    "sort": {"type": "string", "enum": list(_SORTS), "description": "date = newest first, amount = largest first."},
                    "limit": {"type": "integer", "description": "Rows to return, 1-20. Default 20."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "portfolio_summary",
            "description": "Current net worth, total assets and debts, allocation by asset class, debts (balance, APR, "
            "monthly payment), monthly net-worth trend and the user's goals with targets and dates.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tools ────────────────────────────────────────────────────────────────────


def _merchant_key(description: object) -> str:
    """Merchant proxy: first 4 words upper-cased, minus reference codes (words with digits) after the first word."""
    tokens = str(description or "").split()
    if not tokens:
        return "UNKNOWN"
    kept = tokens[:1] + [t for t in tokens[1:] if not any(c.isdigit() for c in t)]
    return " ".join(kept[:4]).upper()[:50]


def _is_transfer(record: dict) -> bool:
    return str(record.get("category") or "").strip().lower() == "transfer"


def _filter(records: list[dict], category: str | None, merchant_contains: str | None) -> list[dict]:
    out = records
    if category:
        wanted = category.strip().lower()
        out = [r for r in out if str(r.get("category") or "").strip().lower() == wanted]
    else:
        out = [r for r in out if not _is_transfer(r)]
    if merchant_contains:
        needle = merchant_contains.strip().lower()
        out = [r for r in out if needle in str(r.get("description") or "").lower()]
    return out


def _group_key(record: dict, group_by: str) -> str:
    if group_by == "month":
        return str(record.get("date") or "")[:7]
    if group_by == "merchant":
        return _merchant_key(record.get("description"))
    return str(record.get("category") or "Uncategorized")


def cash_flow_summary(
    records: list[dict], *, group_by: str = "category", category: str | None = None, merchant_contains: str | None = None
) -> dict:
    """Server-side totals over ``records`` (already date-filtered). Never returns individual rows."""
    if group_by not in _GROUP_BY:
        raise AssistantInputError(f"group_by must be one of {', '.join(_GROUP_BY)}")
    matched = _filter(records, category, merchant_contains)
    income = spend = 0.0
    groups: dict[str, dict] = {}
    for record in matched:
        amount = float(record.get("amount") or 0.0)
        group = groups.setdefault(_group_key(record, group_by), {"spend": 0.0, "income": 0.0, "count": 0})
        group["count"] += 1
        if amount < 0:
            spend -= amount
            group["spend"] -= amount
        else:
            income += amount
            group["income"] += amount
    ranked = sorted(groups.items(), key=lambda kv: (-kv[1]["spend"], -kv[1]["income"], kv[0]))[:_MAX_GROUPS]
    return {
        "income": round(income, 2),
        "spend": round(spend, 2),
        "net": round(income - spend, 2),
        "transaction_count": len(matched),
        "groups": [
            {"key": key, "spend": round(g["spend"], 2), "income": round(g["income"], 2), "count": g["count"]}
            for key, g in ranked
        ],
    }


def _totals(records: list[dict]) -> tuple[float, float]:
    amounts = [float(r.get("amount") or 0.0) for r in records]
    return round(sum(a for a in amounts if a > 0), 2), round(-sum(a for a in amounts if a < 0), 2)


def find_transactions(
    records: list[dict],
    *,
    category: str | None = None,
    merchant_contains: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    sort: str = "date",
    limit: int = _MAX_ROWS,
) -> dict:
    """Matching transactions: totals over every match, at most 20 rows with only the whitelisted fields."""
    if sort not in _SORTS:
        raise AssistantInputError(f"sort must be one of {', '.join(_SORTS)}")
    matched = [
        r
        for r in _filter(records, category, merchant_contains)
        if (min_amount is None or abs(float(r.get("amount") or 0.0)) >= min_amount)
        and (max_amount is None or abs(float(r.get("amount") or 0.0)) <= max_amount)
    ]
    if sort == "amount":
        ordered = sorted(matched, key=lambda r: -abs(float(r.get("amount") or 0.0)))
    else:
        ordered = sorted(matched, key=lambda r: str(r.get("date") or ""), reverse=True)
    rows = [{field: r.get(field) for field in _ROW_FIELDS} for r in ordered[: max(1, min(limit, _MAX_ROWS))]]
    income, spend = _totals(matched)
    return {"match_count": len(matched), "income": income, "spend": spend, "rows_shown": len(rows), "rows": rows}


def portfolio_summary(snapshot: dict) -> dict:
    """The goal advisor's aggregate plus each goal's name, target and date (debts referenced by index)."""
    debts = snapshot.get("debts", [])
    aggregate = build_goal_aggregate(
        snapshot.get("assets", []), debts, snapshot.get("histories", {}), snapshot.get("goals", []),
        asset_kind_names=snapshot.get("asset_kind_names"),
    )
    debt_index = {d["id"]: i for i, d in enumerate(debts)}
    goals = []
    for goal in snapshot.get("goals", []):
        kind = goal.get("kind") or "net_worth"
        entry = {"name": goal.get("name"), "kind": kind}
        if kind == "net_worth":
            entry["target_amount"] = goal.get("target_amount")
        elif kind == "allocation":
            entry["asset_kind"], entry["target_pct"] = goal.get("asset_kind"), goal.get("target_pct")
        elif kind == "debt_payoff":
            entry["debt_index"] = debt_index.get(goal.get("debt_id"))
        entry["target_date"] = goal.get("target_date")
        goals.append(entry)
    aggregate.pop("existing_goals", None)
    return {**aggregate, "goals": goals}


def _optional_number(args: dict, name: str) -> float | None:
    value = args.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AssistantInputError(f"{name} must be a number")
    return float(value)


def _parse_range(args: dict) -> tuple[str, str]:
    def parse(name: str, default: date) -> date:
        raw = args.get(name)
        if raw in (None, ""):
            return default
        try:
            return datetime.strptime(str(raw), "%Y-%m-%d").date()
        except ValueError as exc:
            raise AssistantInputError(f"{name} must be YYYY-MM-DD") from exc

    today = datetime.now(tz=timezone.utc).date()
    end = parse("end", today)
    start = parse("start", end - timedelta(days=_DEFAULT_RANGE_DAYS))
    if start > end:
        raise AssistantInputError("start must be on or before end")
    return start.isoformat(), end.isoformat()


def _optional_str(args: dict, name: str) -> str | None:
    value = args.get(name)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise AssistantInputError(f"{name} must be a string")
    return value


def _run_tool(name: str, raw_arguments: str | None, ctx: SimpleNamespace) -> dict:
    """Execute one tool call. Errors go back to the model as ``{"error": ...}``, never raise."""
    try:
        args = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return {"error": "arguments must be a JSON object"}
    if not isinstance(args, dict):
        return {"error": "arguments must be a JSON object"}
    try:
        if name == "cash_flow_summary":
            start, end = _parse_range(args)
            return cash_flow_summary(
                ctx.load_records(start, end),
                group_by=_optional_str(args, "group_by") or "category",
                category=_optional_str(args, "category"),
                merchant_contains=_optional_str(args, "merchant_contains"),
            )
        if name == "find_transactions":
            start, end = _parse_range(args)
            limit = _optional_number(args, "limit")
            return find_transactions(
                ctx.load_records(start, end),
                category=_optional_str(args, "category"),
                merchant_contains=_optional_str(args, "merchant_contains"),
                min_amount=_optional_number(args, "min_amount"),
                max_amount=_optional_number(args, "max_amount"),
                sort=_optional_str(args, "sort") or "date",
                limit=int(limit) if limit is not None else _MAX_ROWS,
            )
        if name == "portfolio_summary":
            return portfolio_summary(ctx.load_portfolio())
    except AssistantInputError as exc:
        return {"error": str(exc)}
    return {"error": f"unknown tool: {name}"}


# ── Chat loop ────────────────────────────────────────────────────────────────


def _assistant_message(msg: object) -> dict:
    out = {
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ],
    }
    reasoning = getattr(msg, "reasoning_content", None)
    if reasoning:  # DeepSeek thinking mode wants its reasoning echoed back within the same turn
        out["reasoning_content"] = reasoning
    return out


def run_turn(client: object, history: list[dict], message: str, ctx: SimpleNamespace) -> str:
    """One user turn: tool rounds (≤ 5 tool calls), then the model's text answer."""
    today = datetime.now(tz=timezone.utc).date().isoformat()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT.format(today=today)},
        *({"role": m["role"], "content": m["content"]} for m in history[-_HISTORY_MESSAGES:]),
        {"role": "user", "content": message},
    ]
    calls = 0
    while True:
        forced = calls >= _MAX_TOOL_CALLS
        kwargs = {"model": get_deepseek_model(), "messages": messages, "tools": _TOOLS, "temperature": 0.3}
        if forced:
            kwargs["tool_choice"] = "none"
        msg = client.chat.completions.create(**kwargs).choices[0].message
        if not msg.tool_calls or forced:
            return (msg.content or "").replace("**", "").strip()  # replies render as plain text
        messages.append(_assistant_message(msg))
        for tc in msg.tool_calls:
            calls += 1
            result = (
                _run_tool(tc.function.name, tc.function.arguments, ctx)
                if calls <= _MAX_TOOL_CALLS
                else {"error": "tool call limit reached; answer with what you have"}
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, ensure_ascii=False)})


def _make_client() -> object:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise AssistantNotConfigured("AI assistant not configured (DEEPSEEK_API_KEY not set)")
    from openai import OpenAI  # noqa: PLC0415 — lazy: keeps the route tests importable without openai

    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL, timeout=_LLM_TIMEOUT_SECONDS)


# ── Threads ──────────────────────────────────────────────────────────────────


def _threads():
    coll = get_db()[_THREADS_COLLECTION]
    coll.create_index([("user_email", 1), ("updated_at", -1)], background=True)
    return coll


def _oid(thread_id: str) -> ObjectId:
    try:
        return ObjectId(thread_id)
    except (InvalidId, TypeError) as exc:
        raise ThreadNotFound("Thread not found") from exc


def _title(message: str) -> str:
    return message if len(message) <= _TITLE_CHARS else message[: _TITLE_CHARS - 1].rstrip() + "…"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def send_message(
    user_email: str,
    profile_id: str | None,
    thread_id: str | None,
    message: object,
    load_records: Callable[[str, str, str], list[dict]],
    load_portfolio: Callable[[], dict],
    client: object | None = None,
) -> dict:
    """Answer ``message`` in a new or existing thread. Returns ``{thread: {id, title, updated_at}, reply}``."""
    text = message.strip() if isinstance(message, str) else ""
    if not text or len(text) > MAX_MESSAGE_CHARS:
        raise AssistantInputError(f"Message must be 1–{MAX_MESSAGE_CHARS} characters")
    client = client or _make_client()

    coll = _threads()
    thread = None
    if thread_id:
        thread = coll.find_one({"_id": _oid(thread_id), "user_email": user_email})
        if not thread:
            raise ThreadNotFound("Thread not found")
    profile = thread["profile_id"] if thread else (profile_id or "all")
    ctx = SimpleNamespace(load_records=lambda start, end: load_records(start, end, profile), load_portfolio=load_portfolio)

    reply = run_turn(client, thread["messages"] if thread else [], text, ctx)

    now = _now_iso()
    turn = [{"role": "user", "content": text, "at": now}, {"role": "assistant", "content": reply, "at": now}]
    if thread:
        coll.update_one(
            {"_id": thread["_id"], "user_email": user_email},
            {"$push": {"messages": {"$each": turn}}, "$set": {"updated_at": now}},
        )
        summary = {"id": str(thread["_id"]), "title": thread["title"], "updated_at": now}
    else:
        doc = {
            "user_email": user_email,
            "profile_id": profile,
            "title": _title(text),
            "messages": turn,
            "created_at": now,
            "updated_at": now,
        }
        inserted = coll.insert_one(doc)
        summary = {"id": str(inserted.inserted_id), "title": doc["title"], "updated_at": now}
    return {"thread": summary, "reply": reply}
