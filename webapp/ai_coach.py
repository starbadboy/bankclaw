"""AI Coach — generates structured financial review + suggestions from a
user's recent transactions using DeepSeek (OpenAI-compatible API).

Design notes:
- Never sends raw transactions to the LLM. Only aggregates.
- Caches results in Mongo per (user, profile, range) so page loads don't
  hit the LLM. Callers force a refresh explicitly.
- Returns a fixed JSON shape the frontend can render as cards.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import pandas as pd
from openai import OpenAI

from webapp.db import get_db

_CACHE_COLLECTION = "ai_reviews"

_SYSTEM_PROMPT = """You are a pragmatic personal-finance coach reviewing a user's spending.
Analyse the aggregate data and return STRICT JSON only (no markdown fences, no prose outside JSON).

Return this exact shape:
{
  "summary": "one paragraph, at most 3 sentences, big-picture observation",
  "strengths": [
    {"area": "category name", "note": "what they're doing well"}
  ],
  "opportunities": [
    {
      "area": "category name or merchant",
      "severity": "low" | "medium" | "high",
      "issue": "short description of the pattern",
      "action": "one concrete step the user can take",
      "potential_monthly_savings": 0
    }
  ],
  "subscriptions_review": [
    {"merchant": "name", "note": "short recommendation"}
  ],
  "watchouts": [
    {"area": "category", "note": "short flag"}
  ]
}

Rules:
- 2-4 strengths, 3-5 opportunities, up to 3 subscriptions_review, up to 3 watchouts.
- Be specific. Cite numbers from the input when possible.
- `potential_monthly_savings` is an integer SGD estimate (0 if unclear).
- Tone: direct, supportive, Singapore context.
"""


def _ensure_indexes() -> None:
    db = get_db()
    db[_CACHE_COLLECTION].create_index(
        [("user_email", 1), ("profile_id", 1), ("range_days", 1)],
        unique=True,
        background=True,
    )


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def build_aggregate(df: pd.DataFrame, range_days: int) -> dict:
    """Return a compact dict summarising the user's spending patterns."""
    if df.empty:
        return {
            "range_days": range_days,
            "transaction_count": 0,
            "income": 0.0, "spend": 0.0, "net": 0.0, "savings_rate": 0.0,
            "by_category": [], "top_merchants": [], "recurring": [],
        }

    df = df.copy()
    df["amount"] = df["amount"].astype(float)

    income = float(df[df["amount"] > 0]["amount"].sum())
    spend = float(-df[df["amount"] < 0]["amount"].sum())
    net = income - spend
    savings_rate = round((net / income) * 100, 1) if income > 0 else 0.0

    # Prior-period for delta comparison
    cutoff_prev = datetime.now(tz=timezone.utc) - timedelta(days=range_days * 2)
    cutoff_curr = datetime.now(tz=timezone.utc) - timedelta(days=range_days)
    df["_date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    curr_df = df[df["_date"] >= cutoff_curr]
    prev_df = df[(df["_date"] >= cutoff_prev) & (df["_date"] < cutoff_curr)]

    def _by_cat(d: pd.DataFrame) -> dict[str, dict]:
        out: dict[str, dict] = {}
        spending = d[d["amount"] < 0]
        for cat, group in spending.groupby("category"):
            if str(cat).lower() in ("transfer", ""):
                continue
            total = float(-group["amount"].sum())
            count = int(len(group))
            out[str(cat)] = {"total": round(total, 2), "count": count,
                             "avg": round(total / count, 2) if count else 0}
        return out

    curr_cats = _by_cat(curr_df)
    prev_cats = _by_cat(prev_df)
    by_category = []
    for cat, stats in sorted(curr_cats.items(), key=lambda kv: -kv[1]["total"]):
        prev_total = prev_cats.get(cat, {}).get("total", 0.0)
        pct_change = None
        if prev_total > 0:
            pct_change = round(((stats["total"] - prev_total) / prev_total) * 100, 1)
        by_category.append({
            "category": cat,
            "total": stats["total"],
            "count": stats["count"],
            "avg_per_tx": stats["avg"],
            "prev_total": round(prev_total, 2),
            "pct_change_vs_prior": pct_change,
        })

    # Top merchants — group by normalised description prefix
    merchant_totals: Counter = Counter()
    merchant_counts: Counter = Counter()
    for _, row in curr_df[curr_df["amount"] < 0].iterrows():
        desc = str(row["description"]).strip()
        # collapse multi-space + take first 4 words as merchant proxy
        tokens = [t for t in desc.split() if t]
        key = " ".join(tokens[:4]).upper()[:50] if tokens else "UNKNOWN"
        merchant_totals[key] += float(-row["amount"])
        merchant_counts[key] += 1
    top_merchants = [
        {"merchant": k, "total": round(v, 2), "count": merchant_counts[k]}
        for k, v in merchant_totals.most_common(10)
    ]

    # Recurring: same "merchant key" appearing in 2+ distinct calendar months
    month_map: dict[str, set] = defaultdict(set)
    for _, row in curr_df[curr_df["amount"] < 0].iterrows():
        desc = str(row["description"]).strip()
        tokens = [t for t in desc.split() if t]
        key = " ".join(tokens[:4]).upper()[:50] if tokens else "UNKNOWN"
        d = row["_date"]
        if pd.isna(d):
            continue
        month_map[key].add(f"{d.year}-{d.month:02d}")
    recurring = [
        {"merchant": k, "months_seen": len(m),
         "estimated_monthly": round(merchant_totals[k] / max(len(m), 1), 2)}
        for k, m in month_map.items() if len(m) >= 2
    ]
    recurring.sort(key=lambda r: -r["estimated_monthly"])
    recurring = recurring[:12]

    return {
        "range_days": range_days,
        "transaction_count": int(len(curr_df)),
        "income": round(income, 2),
        "spend": round(spend, 2),
        "net": round(net, 2),
        "savings_rate_pct": savings_rate,
        "by_category": by_category,
        "top_merchants": top_merchants,
        "recurring": recurring,
    }


def _call_llm(aggregate: dict) -> dict:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    completion = client.chat.completions.create(
        model="deepseek-chat",
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
        # Strip markdown fences if the model snuck them in
        cleaned = content.strip().strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)


def get_cached(user_email: str, profile_id: str | None, range_days: int) -> dict | None:
    _ensure_indexes()
    doc = get_db()[_CACHE_COLLECTION].find_one(
        {"user_email": user_email, "profile_id": profile_id or "all", "range_days": range_days},
        {"_id": 0},
    )
    return doc


def save_cache(
    user_email: str, profile_id: str | None, range_days: int, review: dict, aggregate: dict
) -> None:
    _ensure_indexes()
    now = _iso_now()
    db = get_db()
    db[_CACHE_COLLECTION].update_one(
        {"user_email": user_email, "profile_id": profile_id or "all", "range_days": range_days},
        {
            "$set": {
                "review": review,
                "aggregate": aggregate,
                "generated_at": now,
            },
            "$setOnInsert": {"user_email": user_email, "profile_id": profile_id or "all",
                             "range_days": range_days},
        },
        upsert=True,
    )


def generate_review(
    *, user_email: str, df: pd.DataFrame, range_days: int,
    profile_id: str | None = None, force_refresh: bool = False,
) -> dict:
    """Returns {review, generated_at, from_cache, aggregate}."""
    if not force_refresh:
        cached = get_cached(user_email, profile_id, range_days)
        if cached and cached.get("review"):
            return {
                "review": cached["review"],
                "generated_at": cached.get("generated_at"),
                "from_cache": True,
                "aggregate": cached.get("aggregate"),
            }

    aggregate = build_aggregate(df, range_days=range_days)
    if aggregate["transaction_count"] == 0:
        empty = {
            "summary": "Not enough transactions yet to review. Import a few statements or add manual entries, then come back.",
            "strengths": [], "opportunities": [], "subscriptions_review": [], "watchouts": [],
        }
        save_cache(user_email, profile_id, range_days, empty, aggregate)
        return {"review": empty, "generated_at": _iso_now(), "from_cache": False, "aggregate": aggregate}

    review = _call_llm(aggregate)
    save_cache(user_email, profile_id, range_days, review, aggregate)
    return {"review": review, "generated_at": _iso_now(), "from_cache": False, "aggregate": aggregate}
