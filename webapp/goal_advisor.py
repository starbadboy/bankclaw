"""AI goal suggestions — proposes 3 to 5 portfolio goals from aggregates only.

Mirrors ``ai_coach``: DeepSeek via the OpenAI client, strict JSON, one cached
document per user in Mongo (``ai_goal_suggestions``) with dismissed ids.
The aggregate never carries asset names, tickers, units or transactions —
debts are referred to by index so the model can name one without seeing it.
This module imports neither pandas nor openai at import time (route tests stub pandas).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
from datetime import datetime, timezone

from webapp.db import get_db
from webapp.deepseek_config import DEEPSEEK_BASE_URL, get_deepseek_model

_CACHE_COLLECTION = "ai_goal_suggestions"
_KINDS = {"net_worth", "debt_payoff", "allocation"}
_PRIORITIES = {"low", "medium", "high"}
_MAX_SUGGESTIONS = 5
_LLM_TIMEOUT_SECONDS = 180  # DeepSeek structured output has been observed at ~100 s
# ponytail: one generation at a time process-wide; per-user locks or a Mongo lease if users ever queue behind each other.
_GEN_LOCK = threading.Lock()


class AdvisorNotConfigured(ValueError):
    """Raised when a generation is needed but DEEPSEEK_API_KEY is not set."""


_BUILTIN_KIND_NAMES = {
    "cash": "Cash & savings",
    "equities": "Equities",
    "bonds": "Bonds",
    "retirement": "Retirement",
    "property": "Property",
    "crypto": "Crypto",
}

_SYSTEM_PROMPT = """You are a pragmatic personal-finance coach helping a user in Singapore set portfolio goals.
You receive aggregate portfolio data (no account names). Propose 3 to 5 concrete goals and return STRICT JSON only.

Return this exact shape:
{
  "suggestions": [
    {
      "kind": "net_worth" | "debt_payoff" | "allocation",
      "name": "short goal name",
      "target_amount": 0,          // net_worth only, SGD
      "debt_index": 0,             // debt_payoff only: index into the input debts list
      "asset_kind": "equities",    // allocation only: a kind from the input allocation list
      "target_pct": 0,             // allocation only: 1-100, share of total assets
      "target_date": "YYYY-MM-DD" | null,
      "rationale": "one sentence citing numbers from the input",
      "priority": "low" | "medium" | "high"
    }
  ]
}

Rules:
- Use the net_worth_trend to size and date net_worth goals realistically (reachable within 6-36 months on trend, or a stretch clearly labelled).
- Prefer paying off the highest-APR debt first; only suggest debts that exist in the input.
- Allocation goals must move a class toward a sensible long-term mix; do not repeat existing_goals.
- Tone: direct, supportive. No prose outside the JSON.
"""


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _ensure_indexes() -> None:
    get_db()[_CACHE_COLLECTION].create_index([("user_email", 1)], unique=True, background=True)


def _latest_on_or_before(entries: list[dict], month: str) -> float | None:
    best = None
    for entry in entries:
        date = str(entry.get("as_of_date") or "")
        if date[:7] <= month and (best is None or date > best[0]):
            best = (date, float(entry.get("value") or 0.0))
    return None if best is None else best[1]


def _net_worth_trend(assets: list[dict], debts: list[dict], histories: dict, months: int = 12) -> list[dict]:
    """Month-end net worth for the last ``months`` months that have any valuation."""
    all_months = sorted(
        {str(e.get("as_of_date") or "")[:7] for entries in histories.values() for e in entries if e.get("as_of_date")}
    )
    all_months = all_months[-months:]
    trend = []
    for month in all_months:
        total = 0.0
        for asset in assets:
            value = _latest_on_or_before(histories.get(f"asset:{asset['id']}", []), month)
            if value is not None:
                total += value
        for debt in debts:
            value = _latest_on_or_before(histories.get(f"debt:{debt['id']}", []), month)
            if value is not None:
                total -= value
        trend.append({"date": month, "net": round(total, 2)})
    return trend


def _goal_target(goal: dict) -> float:
    kind = goal.get("kind") or "net_worth"
    if kind == "net_worth":
        return float(goal.get("target_amount") or 0.0)
    if kind == "allocation":
        return float(goal.get("target_pct") or 0.0)
    return 0


def build_goal_aggregate(
    assets: list[dict], debts: list[dict], histories: dict, goals: list[dict], *, asset_kind_names: dict | None = None
) -> dict:
    """Aggregates only: totals, per-class allocation, indexed debts, monthly net-worth trend, existing goals."""
    names = {**_BUILTIN_KIND_NAMES, **(asset_kind_names or {})}
    total_assets = round(sum(float(a.get("value") or 0.0) for a in assets), 2)
    total_debts = round(sum(float(d.get("value") or 0.0) for d in debts), 2)
    by_kind: dict[str, float] = {}
    for asset in assets:
        by_kind[asset["kind"]] = by_kind.get(asset["kind"], 0.0) + float(asset.get("value") or 0.0)
    allocation = [
        {
            "kind": kind,
            "name": names.get(kind, kind),
            "pct": round(value / total_assets * 100, 1) if total_assets else 0.0,
            "value": round(value, 2),
        }
        for kind, value in sorted(by_kind.items(), key=lambda kv: -kv[1])
    ]
    net = round(total_assets - total_debts, 2)
    return {
        "net_worth": net,
        "total_assets": total_assets,
        "total_debts": total_debts,
        "allocation": allocation,
        "debts": [
            {
                "index": i,
                "kind": d.get("kind"),
                "balance": round(float(d.get("value") or 0.0), 2),
                "apr": float(d.get("apr") or 0.0),
                "monthly": float(d.get("monthly") or 0.0),
            }
            for i, d in enumerate(debts)
        ],
        "net_worth_trend": _net_worth_trend(assets, debts, histories),
        "existing_goals": [{"kind": g.get("kind") or "net_worth", "target": _goal_target(g)} for g in goals],
    }


def _suggestion_id(kind: str, name: str, target: object) -> str:
    return hashlib.sha1(f"{kind}|{name}|{target}".encode()).hexdigest()[:12]


def _is_duplicate(candidate: dict, existing_goals: list[dict]) -> bool:
    for goal in existing_goals:
        if (goal.get("kind") or "net_worth") != candidate["kind"]:
            continue
        if candidate["kind"] == "debt_payoff" and goal.get("debt_id") == candidate["debt_id"]:
            return True
        if candidate["kind"] == "allocation" and goal.get("asset_kind") == candidate["asset_kind"]:
            return True
        if candidate["kind"] == "net_worth":
            target = float(goal.get("target_amount") or 0.0)
            if target and abs(target - candidate["target_amount"]) / target <= 0.01:
                return True
    return False


def _as_number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_date(value: object) -> str | None:
    text = str(value or "")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def normalize_suggestions(
    raw: dict, debts: list[dict], existing_goals: list[dict], *, asset_kinds: set[str]
) -> list[dict]:
    """Validate model output into ready-to-create goals; drop anything malformed, out of range or duplicate."""
    out: list[dict] = []
    for item in (raw or {}).get("suggestions") or []:
        if not isinstance(item, dict) or item.get("kind") not in _KINDS:
            continue
        kind = item["kind"]
        name = str(item.get("name") or "").strip()[:80]
        candidate = {
            "kind": kind,
            "name": name,
            "target_amount": None,
            "target_pct": None,
            "asset_kind": None,
            "debt_id": None,
            "target_date": _as_date(item.get("target_date")),
            "rationale": str(item.get("rationale") or "").strip()[:240],
            "priority": item.get("priority") if item.get("priority") in _PRIORITIES else "medium",
        }
        if kind == "net_worth":
            amount = _as_number(item.get("target_amount"))
            if not amount or amount <= 0:
                continue
            candidate["target_amount"] = round(amount, 2)
            target_key = candidate["target_amount"]
        elif kind == "debt_payoff":
            index = _as_number(item.get("debt_index"))
            if index is None or not 0 <= int(index) < len(debts):
                continue
            candidate["debt_id"] = debts[int(index)]["id"]
            candidate["name"] = name or f"Pay off {debts[int(index)].get('name', 'debt')}"
            target_key = candidate["debt_id"]
        else:
            pct = _as_number(item.get("target_pct"))
            if pct is None or not 1 <= pct <= 100 or item.get("asset_kind") not in asset_kinds:
                continue
            candidate["target_pct"] = round(pct, 1)
            candidate["asset_kind"] = item["asset_kind"]
            target_key = f"{candidate['asset_kind']}:{candidate['target_pct']}"
        if not candidate["name"] or _is_duplicate(candidate, existing_goals):
            continue
        candidate["id"] = _suggestion_id(kind, candidate["name"], target_key)
        if any(s["id"] == candidate["id"] for s in out):
            continue
        out.append(candidate)
        if len(out) == _MAX_SUGGESTIONS:
            break
    return out


def _call_llm(aggregate: dict) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise AdvisorNotConfigured("DEEPSEEK_API_KEY not set")
    from openai import OpenAI  # noqa: PLC0415 — lazy: keeps this module light and the route tests importable

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL, timeout=_LLM_TIMEOUT_SECONDS)
    completion = client.chat.completions.create(
        model=get_deepseek_model(),
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(aggregate, ensure_ascii=False)},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        cleaned = content.strip().strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)


def _visible(doc: dict) -> list[dict]:
    dismissed = set(doc.get("dismissed_ids") or [])
    return [s for s in doc.get("suggestions") or [] if s.get("id") not in dismissed]


def get_suggestions(
    user_email: str, build_portfolio, *, force_refresh: bool = False, dismiss: str | None = None
) -> dict:  # noqa: ANN001
    """Return ``{suggestions, snapshot, generated_at, from_cache}`` for the user, generating when needed.

    ``build_portfolio`` is a zero-arg callable returning {assets, debts, histories, goals, asset_kind_names};
    it is only invoked when a generation actually happens. Raises ``AdvisorNotConfigured`` when generation
    is required and no API key is set.
    """
    _ensure_indexes()
    coll = get_db()[_CACHE_COLLECTION]
    cached = coll.find_one({"user_email": user_email}, {"_id": 0})

    if dismiss and cached:
        coll.update_one({"user_email": user_email}, {"$addToSet": {"dismissed_ids": dismiss}})
        cached = {**cached, "dismissed_ids": [*(cached.get("dismissed_ids") or []), dismiss]}
    if cached and not force_refresh:
        return _from_doc(cached)

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise AdvisorNotConfigured("DEEPSEEK_API_KEY not set")
    with _GEN_LOCK:  # late arrivals read what the first generation saved
        if not force_refresh:
            fresh = coll.find_one({"user_email": user_email}, {"_id": 0})
            if fresh:
                return _from_doc(fresh)
        return _generate(user_email, coll, build_portfolio())


def _from_doc(doc: dict) -> dict:
    return {
        "suggestions": _visible(doc),
        "snapshot": doc.get("snapshot"),
        "generated_at": doc.get("generated_at"),
        "from_cache": True,
    }


def _generate(user_email: str, coll, portfolio: dict) -> dict:  # noqa: ANN001
    assets, debts, goals = portfolio["assets"], portfolio["debts"], portfolio["goals"]
    aggregate = build_goal_aggregate(
        assets, debts, portfolio.get("histories") or {}, goals, asset_kind_names=portfolio.get("asset_kind_names")
    )
    raw = _call_llm(aggregate)
    suggestions = normalize_suggestions(
        raw,
        debts,
        goals,
        asset_kinds={a["kind"] for a in assets}
        | set(_BUILTIN_KIND_NAMES)
        | set(portfolio.get("asset_kind_names") or {}),
    )
    snapshot = {"net": aggregate["net_worth"], "goal_count": len(goals)}
    now = _iso_now()
    coll.update_one(
        {"user_email": user_email},
        {
            "$set": {"suggestions": suggestions, "snapshot": snapshot, "generated_at": now, "dismissed_ids": []},
            "$setOnInsert": {"user_email": user_email},
        },
        upsert=True,
    )
    return {"suggestions": suggestions, "snapshot": snapshot, "generated_at": now, "from_cache": False}
