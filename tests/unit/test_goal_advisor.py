import json
from unittest.mock import MagicMock, patch

import pytest

from webapp import goal_advisor
from webapp.goal_advisor import AdvisorNotConfigured, build_goal_aggregate, get_suggestions, normalize_suggestions

ASSETS = [
    {"id": "a1", "name": "DBS Multiplier", "kind": "cash", "value": 54000.0, "ticker": None, "units": None},
    {"id": "a2", "name": "Endowus Equities", "kind": "equities", "value": 21000.0, "ticker": "ADSK", "units": 672},
]
DEBTS = [
    {"id": "d1", "name": "Car loan", "kind": "loan", "value": 13800.0, "apr": 2.8, "monthly": 600.0, "base": 18000.0}
]
HISTORIES = {
    "asset:a1": [
        {"as_of_date": "2026-02-01", "value": 42000.0},
        {"as_of_date": "2026-05-01", "value": 48000.0},
        {"as_of_date": "2026-08-01", "value": 54000.0},
    ],
    "asset:a2": [{"as_of_date": "2026-02-01", "value": 16000.0}, {"as_of_date": "2026-08-01", "value": 21000.0}],
    "debt:d1": [{"as_of_date": "2026-02-01", "value": 18000.0}, {"as_of_date": "2026-08-01", "value": 13800.0}],
}
GOALS = [
    {"id": "g1", "kind": "net_worth", "name": "First 100k", "target_amount": 100000.0, "target_date": "2027-12-31"},
    {"id": "g2", "kind": "debt_payoff", "name": "Pay off Car loan", "debt_id": "d1", "baseline": 13800.0},
]


def test_aggregate_contains_only_aggregates_and_never_names_or_tickers():
    agg = build_goal_aggregate(
        ASSETS, DEBTS, HISTORIES, GOALS, asset_kind_names={"cash": "Cash & savings", "equities": "Equities"}
    )

    assert agg["net_worth"] == 61200.0
    assert agg["total_assets"] == 75000.0 and agg["total_debts"] == 13800.0
    assert agg["allocation"] == [
        {"kind": "cash", "name": "Cash & savings", "pct": 72.0, "value": 54000.0},
        {"kind": "equities", "name": "Equities", "pct": 28.0, "value": 21000.0},
    ]
    assert agg["debts"] == [{"index": 0, "kind": "loan", "balance": 13800.0, "apr": 2.8, "monthly": 600.0}]
    assert agg["net_worth_trend"][0] == {"date": "2026-02", "net": 40000.0}
    assert agg["net_worth_trend"][-1] == {"date": "2026-08", "net": 61200.0}
    assert agg["existing_goals"] == [
        {"kind": "net_worth", "target": 100000.0},
        {"kind": "debt_payoff", "target": 0},
    ]
    blob = json.dumps(agg)
    for forbidden in ("DBS Multiplier", "Endowus", "ADSK", "Car loan", "672", "units", "ticker"):
        assert forbidden not in blob


def test_normalize_drops_malformed_duplicates_and_maps_debt_index_to_id():
    raw = {
        "suggestions": [
            {
                "kind": "net_worth",
                "name": "Reach 150k",
                "target_amount": 150000,
                "target_date": "2028-12-31",
                "rationale": "Trend supports it",
                "priority": "high",
            },
            {
                "kind": "net_worth",
                "name": "Dup of existing",
                "target_amount": 100500,
                "rationale": "x",
                "priority": "low",
            },
            {
                "kind": "debt_payoff",
                "name": "Clear the loan",
                "debt_index": 0,
                "target_date": "2027-03-31",
                "rationale": "APR",
                "priority": "medium",
            },
            {"kind": "debt_payoff", "name": "Ghost debt", "debt_index": 7, "rationale": "x", "priority": "low"},
            {
                "kind": "allocation",
                "name": "Equities 40%",
                "asset_kind": "equities",
                "target_pct": 40,
                "rationale": "Diversify",
                "priority": "medium",
            },
            {
                "kind": "allocation",
                "name": "Bad pct",
                "asset_kind": "equities",
                "target_pct": 140,
                "rationale": "x",
                "priority": "low",
            },
            {"kind": "lottery", "name": "Nope", "target_amount": 1, "rationale": "x", "priority": "low"},
            {"kind": "net_worth", "name": "No number", "rationale": "x", "priority": "low"},
        ]
    }
    out = normalize_suggestions(raw, DEBTS, GOALS[:1], asset_kinds={"cash", "equities"})

    kinds = [s["kind"] for s in out]
    assert kinds == [
        "net_worth",
        "debt_payoff",
        "allocation",
    ]  # near-duplicate net-worth, ghost debt, bad pct, unknown kind dropped
    assert [s["kind"] for s in normalize_suggestions(raw, DEBTS, GOALS, asset_kinds={"cash", "equities"})] == [
        "net_worth",
        "allocation",
    ]  # existing debt goal deduped
    assert out[1]["debt_id"] == "d1" and "debt_index" not in out[1]
    assert out[2]["target_pct"] == 40.0 and out[2]["asset_kind"] == "equities"
    assert out[0]["target_date"] == "2028-12-31" and out[0]["priority"] == "high"
    assert all(len(s["id"]) == 12 for s in out)
    assert (
        out[0]["id"] == normalize_suggestions(raw, DEBTS, GOALS[:1], asset_kinds={"cash", "equities"})[0]["id"]
    )  # stable ids


def test_normalize_caps_at_five_and_normalises_priority():
    raw = {
        "suggestions": [
            {
                "kind": "net_worth",
                "name": f"G{i}",
                "target_amount": 200000 + i * 1000,
                "rationale": "r",
                "priority": "urgent",
            }
            for i in range(8)
        ]
    }
    out = normalize_suggestions(raw, [], [], asset_kinds=set())
    assert len(out) == 5
    assert {s["priority"] for s in out} == {"medium"}  # unknown priority → medium


def _advisor_db():
    db = MagicMock()
    coll = MagicMock()
    db.__getitem__.return_value = coll
    return db, coll


PORTFOLIO = {
    "assets": ASSETS,
    "debts": DEBTS,
    "histories": HISTORIES,
    "goals": GOALS,
    "asset_kind_names": {"cash": "Cash", "equities": "Equities"},
}
LLM_RAW = {
    "suggestions": [
        {
            "kind": "allocation",
            "name": "Equities 40%",
            "asset_kind": "equities",
            "target_pct": 40,
            "rationale": "Diversify",
            "priority": "medium",
        }
    ]
}


def test_get_suggestions_generates_once_then_serves_cache_and_filters_dismissed(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    db, coll = _advisor_db()
    coll.find_one.return_value = None
    with (
        patch("webapp.goal_advisor.get_db", return_value=db),
        patch("webapp.goal_advisor._call_llm", return_value=LLM_RAW) as llm,
    ):
        first = get_suggestions("owner@example.com", lambda: PORTFOLIO)
    assert llm.call_count == 1
    assert first["from_cache"] is False
    assert first["snapshot"] == {"net": 61200.0, "goal_count": 2}
    assert first["suggestions"][0]["kind"] == "allocation"
    saved = coll.update_one.call_args.args[1]["$set"]
    assert (
        saved["suggestions"] == first["suggestions"]
        and saved["snapshot"] == first["snapshot"]
        and saved["dismissed_ids"] == []
    )

    sid = first["suggestions"][0]["id"]
    coll.find_one.return_value = {
        "suggestions": first["suggestions"],
        "snapshot": first["snapshot"],
        "generated_at": "2026-08-26T00:00:00+00:00",
        "dismissed_ids": [],
    }
    with patch("webapp.goal_advisor.get_db", return_value=db), patch("webapp.goal_advisor._call_llm") as llm:
        cached = get_suggestions("owner@example.com", lambda: PORTFOLIO)
        dismissed = get_suggestions("owner@example.com", lambda: PORTFOLIO, dismiss=sid)
    llm.assert_not_called()
    assert cached["from_cache"] is True and cached["suggestions"][0]["id"] == sid
    assert dismissed["suggestions"] == []
    assert coll.update_one.call_args.args[1]["$addToSet"] == {"dismissed_ids": sid}


def test_get_suggestions_force_refresh_regenerates_and_requires_key(monkeypatch):
    db, coll = _advisor_db()
    coll.find_one.return_value = {
        "suggestions": [],
        "snapshot": {"net": 1, "goal_count": 0},
        "generated_at": "x",
        "dismissed_ids": ["old"],
    }
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch("webapp.goal_advisor.get_db", return_value=db):
        with pytest.raises(AdvisorNotConfigured):
            get_suggestions("owner@example.com", lambda: PORTFOLIO, force_refresh=True)
        coll.update_one.assert_not_called()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    with (
        patch("webapp.goal_advisor.get_db", return_value=db),
        patch("webapp.goal_advisor._call_llm", return_value=LLM_RAW),
    ):
        fresh = get_suggestions("owner@example.com", lambda: PORTFOLIO, force_refresh=True)
    assert fresh["from_cache"] is False
    assert coll.update_one.call_args.args[1]["$set"]["dismissed_ids"] == []  # refresh resets dismissals


def test_module_does_not_import_pandas_or_openai_at_import_time():
    import sys

    assert "webapp.goal_advisor" in sys.modules
    src = open(goal_advisor.__file__).read()
    assert "\nimport pandas" not in src and "\nfrom openai" not in src


def test_concurrent_generation_for_one_user_calls_the_model_once(monkeypatch):
    import threading
    import time

    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    db, coll = _advisor_db()
    state = {"doc": None}
    coll.find_one.side_effect = lambda *a, **k: state["doc"]

    def save(_filter, update, **_):
        state["doc"] = {**update["$set"], "user_email": "owner@example.com"}

    coll.update_one.side_effect = save

    def slow_llm(_agg):
        time.sleep(0.2)
        return LLM_RAW

    results = []
    with (
        patch("webapp.goal_advisor.get_db", return_value=db),
        patch("webapp.goal_advisor._call_llm", side_effect=slow_llm) as llm,
    ):
        threads = [
            threading.Thread(target=lambda: results.append(get_suggestions("owner@example.com", lambda: PORTFOLIO)))
            for _ in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert llm.call_count == 1
    assert len(results) == 3 and all(r["suggestions"] for r in results)


def test_cached_reads_never_build_the_portfolio_snapshot():
    db, coll = _advisor_db()
    coll.find_one.return_value = {"suggestions": [], "snapshot": {"net": 1, "goal_count": 0}, "generated_at": "x", "dismissed_ids": []}
    builder = MagicMock(return_value=PORTFOLIO)
    with patch("webapp.goal_advisor.get_db", return_value=db):
        get_suggestions("owner@example.com", builder)
        get_suggestions("owner@example.com", builder, dismiss="abc")
    builder.assert_not_called()


def test_llm_client_is_created_with_a_timeout(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    fake_openai = MagicMock()
    fake_openai.return_value.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content='{"suggestions": []}'))]
    with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=fake_openai)}):
        goal_advisor._call_llm({"net_worth": 1})
    assert fake_openai.call_args.kwargs["timeout"] >= 60
