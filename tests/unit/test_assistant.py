import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId

from webapp import assistant
from webapp.assistant import (
    AssistantInputError,
    AssistantNotConfigured,
    ThreadNotFound,
    cash_flow_summary,
    delete_thread,
    find_transactions,
    get_thread,
    is_configured,
    list_threads,
    portfolio_summary,
    run_turn,
    send_message,
)

RECORDS = [
    {"date": "2026-09-02", "description": "GRAB FOOD SINGAPORE 123", "amount": -20.5, "category": "Food",
     "user_email": "owner@example.com", "bank": "DBS", "profile_id": "p1"},
    {"date": "2026-09-15", "description": "GRAB FOOD SINGAPORE 999", "amount": -9.5, "category": "Food"},
    {"date": "2026-09-30", "description": "NTUC FAIRPRICE", "amount": -50.0, "category": "Groceries"},
    {"date": "2026-10-01", "description": "SALARY ACME", "amount": 5000.0, "category": "Income"},
    {"date": "2026-10-03", "description": "TRANSFER TO SAVINGS", "amount": -1000.0, "category": "Transfer"},
]


def _tool_call(name, args, call_id="c1"):
    return SimpleNamespace(id=call_id, type="function", function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def _reply(content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    """Scripted chat.completions.create: returns the queued replies in order, repeating the last one."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs, default=str)))
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def _ctx(records=RECORDS):
    load = MagicMock(return_value=records)
    return SimpleNamespace(load_records=load, load_portfolio=MagicMock(return_value={})), load


# ── cash_flow_summary ────────────────────────────────────────────────────────


def test_cash_flow_totals_exclude_transfers_and_group_by_category():
    out = cash_flow_summary(RECORDS, group_by="category")
    assert out["income"] == 5000.0
    assert out["spend"] == 80.0  # transfer excluded, like the dashboard
    assert out["net"] == 4920.0
    assert out["transaction_count"] == 4
    assert [g["key"] for g in out["groups"]] == ["Groceries", "Food", "Income"]  # by spend desc, no Transfer
    assert out["groups"][1] == {"key": "Food", "spend": 30.0, "income": 0.0, "count": 2}


def test_cash_flow_filters_by_category_and_merchant_case_insensitively():
    by_cat = cash_flow_summary(RECORDS, category="food")
    by_merchant = cash_flow_summary(RECORDS, merchant_contains="grab", group_by="merchant")
    assert by_cat["spend"] == 30.0 and by_cat["transaction_count"] == 2
    assert by_merchant["spend"] == 30.0
    assert by_merchant["groups"] == [{"key": "GRAB FOOD SINGAPORE", "spend": 30.0, "income": 0.0, "count": 2}]


def test_cash_flow_month_grouping_and_explicit_transfer_filter():
    by_month = cash_flow_summary(RECORDS, group_by="month")
    assert {g["key"] for g in by_month["groups"]} == {"2026-09", "2026-10"}
    transfers = cash_flow_summary(RECORDS, category="Transfer")
    assert transfers["spend"] == 1000.0  # asked for explicitly → counted


def test_cash_flow_caps_groups_at_25_and_never_returns_rows():
    many = [{"date": "2026-09-01", "description": f"SHOP {i}", "amount": -1.0 - i, "category": f"C{i}"} for i in range(40)]
    out = cash_flow_summary(many, group_by="category")
    assert len(out["groups"]) == 25
    assert out["groups"][0]["key"] == "C39"
    assert "rows" not in out and "description" not in json.dumps(out)


def test_cash_flow_on_empty_records():
    out = cash_flow_summary([], group_by="category")
    assert out == {"income": 0.0, "spend": 0.0, "net": 0.0, "transaction_count": 0, "groups": []}


def test_merchant_key_drops_reference_codes_but_keeps_a_leading_brand():
    assert assistant._merchant_key("GRAB FOOD SINGAPORE A1") == "GRAB FOOD SINGAPORE"
    assert assistant._merchant_key("7-ELEVEN CLEMENTI 0123 SG") == "7-ELEVEN CLEMENTI SG"
    assert assistant._merchant_key("  ") == "UNKNOWN"


# ── find_transactions ────────────────────────────────────────────────────────


def test_find_transactions_returns_whitelisted_rows_newest_first():
    out = find_transactions(RECORDS, merchant_contains="grab")
    assert out["match_count"] == 2 and out["spend"] == 30.0
    assert out["rows"] == [
        {"date": "2026-09-15", "description": "GRAB FOOD SINGAPORE 999", "amount": -9.5, "category": "Food"},
        {"date": "2026-09-02", "description": "GRAB FOOD SINGAPORE 123", "amount": -20.5, "category": "Food"},
    ]
    assert "user_email" not in json.dumps(out) and "DBS" not in json.dumps(out) and "p1" not in json.dumps(out)


def test_find_transactions_caps_rows_at_20_but_totals_cover_every_match():
    many = [{"date": f"2026-09-{(i % 28) + 1:02d}", "description": f"SHOP {i}", "amount": -2.0, "category": "Misc"} for i in range(50)]
    out = find_transactions(many, limit=500)
    assert out["match_count"] == 50 and out["spend"] == 100.0
    assert len(out["rows"]) == 20 and out["rows_shown"] == 20
    assert len(find_transactions(many, limit=3)["rows"]) == 3


def test_find_transactions_filters_by_absolute_amount_and_sorts_by_size():
    out = find_transactions(RECORDS, min_amount=10, max_amount=60, sort="amount")
    assert [r["amount"] for r in out["rows"]] == [-50.0, -20.5]  # transfer + salary excluded by filters
    with pytest.raises(AssistantInputError):
        find_transactions(RECORDS, sort="random")


def test_run_turn_find_transactions_rejects_non_numeric_amounts():
    client = FakeClient(_reply(tool_calls=[_tool_call("find_transactions", {"min_amount": "lots"})]), _reply(content="ok"))
    ctx, load = _ctx()
    run_turn(client, [], "q", ctx)
    assert "error" in json.loads(client.calls[1]["messages"][-1]["content"])


# ── portfolio_summary ────────────────────────────────────────────────────────

SNAPSHOT = {
    "assets": [{"id": "a1", "name": "DBS Multiplier", "kind": "cash", "value": 50000.0, "ticker": None}],
    "debts": [{"id": "d1", "name": "Car loan", "kind": "loan", "value": 10000.0, "apr": 2.8, "monthly": 600.0}],
    "histories": {"asset:a1": [{"as_of_date": "2026-09-01", "value": 50000.0}],
                  "debt:d1": [{"as_of_date": "2026-09-01", "value": 10000.0}]},
    "goals": [
        {"id": "g1", "kind": "net_worth", "name": "First 100k", "target_amount": 100000.0, "target_date": "2027-12-31"},
        {"id": "g2", "kind": "debt_payoff", "name": "Kill car loan", "debt_id": "d1", "target_date": None},
    ],
    "asset_kind_names": {},
}


def test_portfolio_summary_reports_net_worth_and_named_goals():
    out = portfolio_summary(SNAPSHOT)
    assert out["net_worth"] == 40000.0 and out["total_debts"] == 10000.0
    assert out["goals"] == [
        {"name": "First 100k", "kind": "net_worth", "target_amount": 100000.0, "target_date": "2027-12-31"},
        {"name": "Kill car loan", "kind": "debt_payoff", "debt_index": 0, "target_date": None},
    ]
    assert out["debts"][0]["balance"] == 10000.0


def test_run_turn_loads_portfolio_only_when_the_tool_is_used():
    ctx, _ = _ctx()
    ctx.load_portfolio.return_value = SNAPSHOT
    run_turn(FakeClient(_reply(content="hi")), [], "hello", ctx)
    ctx.load_portfolio.assert_not_called()
    client = FakeClient(_reply(tool_calls=[_tool_call("portfolio_summary", {})]), _reply(content="40k"))
    run_turn(client, [], "net worth?", ctx)
    ctx.load_portfolio.assert_called_once()
    assert json.loads(client.calls[1]["messages"][-1]["content"])["net_worth"] == 40000.0


# ── run_turn ─────────────────────────────────────────────────────────────────


def test_run_turn_dispatches_tool_with_date_range_and_returns_final_answer():
    client = FakeClient(
        _reply(tool_calls=[_tool_call("cash_flow_summary", {"start": "2026-09-01", "end": "2026-09-30", "category": "Food"})]),
        _reply(content="You spent SGD 30.00 on Food."),
    )
    ctx, load = _ctx()
    reply = run_turn(client, [], "How much on food in September?", ctx)
    assert reply == "You spent SGD 30.00 on Food."
    load.assert_called_once_with("2026-09-01", "2026-09-30")
    tool_msg = client.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert json.loads(tool_msg["content"])["spend"] == 30.0


def test_run_turn_caps_tool_calls_at_five_then_forces_an_answer():
    looping = _reply(tool_calls=[_tool_call("cash_flow_summary", {}, "a"), _tool_call("cash_flow_summary", {}, "b")])
    client = FakeClient(looping, looping, looping, _reply(content="Here is what I found."))
    ctx, load = _ctx()
    reply = run_turn(client, [], "loop", ctx)
    assert reply == "Here is what I found."
    assert load.call_count == 5
    assert client.calls[-1]["tool_choice"] == "none"
    tool_msgs = [m for m in client.calls[-1]["messages"] if m["role"] == "tool"]
    assert len(tool_msgs) == 6  # every tool call is answered, the 6th with a limit error
    assert "limit" in json.loads(tool_msgs[-1]["content"])["error"]


def test_run_turn_sends_only_the_last_20_history_messages():
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}", "at": "x"} for i in range(30)]
    client = FakeClient(_reply(content="ok"))
    run_turn(client, history, "next", _ctx()[0])
    sent = client.calls[0]["messages"]
    assert sent[0]["role"] == "system"
    assert [m["content"] for m in sent[1:-1]] == [f"m{i}" for i in range(10, 30)]
    assert all("at" not in m for m in sent)
    assert sent[-1] == {"role": "user", "content": "next"}


def test_run_turn_returns_errors_to_the_model_for_unknown_tools_and_bad_args():
    bad = SimpleNamespace(id="x", type="function", function=SimpleNamespace(name="cash_flow_summary", arguments="{not json"))
    client = FakeClient(
        _reply(tool_calls=[_tool_call("drop_tables", {}, "u"), bad,
                           _tool_call("cash_flow_summary", {"start": "2026-13-01"}, "d")]),
        _reply(content="Sorry."),
    )
    ctx, load = _ctx()
    assert run_turn(client, [], "q", ctx) == "Sorry."
    errors = [json.loads(m["content"])["error"] for m in client.calls[1]["messages"] if m["role"] == "tool"]
    assert len(errors) == 3
    load.assert_not_called()


# ── send_message ─────────────────────────────────────────────────────────────


def _threads_db():
    db = MagicMock()
    coll = MagicMock()
    db.__getitem__.side_effect = lambda name: coll if name == "assistant_threads" else MagicMock()
    return db, coll


def test_send_message_rejects_empty_and_too_long_messages():
    for bad in ("", "   ", "x" * 2001, None, 5):
        with pytest.raises(AssistantInputError):
            send_message("owner@example.com", "all", None, bad, MagicMock(), MagicMock(), client=FakeClient(_reply("x")))


def test_send_message_without_api_key_raises_not_configured(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(AssistantNotConfigured):
        send_message("owner@example.com", "all", None, "hi", MagicMock(), MagicMock())


def test_send_message_creates_a_thread_only_after_a_successful_reply():
    db, coll = _threads_db()
    coll.insert_one.return_value.inserted_id = ObjectId()
    load = MagicMock(return_value=RECORDS)
    client = FakeClient(_reply(tool_calls=[_tool_call("cash_flow_summary", {})]), _reply(content="Answer"))
    question = "What did I spend on food last month? " * 5
    with patch("webapp.assistant.get_db", return_value=db):
        out = send_message("owner@example.com", "p1", None, question, load, MagicMock(), client=client)
    doc = coll.insert_one.call_args.args[0]
    assert doc["user_email"] == "owner@example.com" and doc["profile_id"] == "p1"
    assert len(doc["title"]) <= 60 and question.startswith(doc["title"].rstrip("…").rstrip())
    assert [(m["role"], m["content"]) for m in doc["messages"]] == [("user", question.strip()), ("assistant", "Answer")]
    assert load.call_args.args[2] == "p1"
    assert out["reply"] == "Answer" and out["thread"]["id"] == str(coll.insert_one.return_value.inserted_id)


def test_send_message_failure_writes_nothing():
    db, coll = _threads_db()

    class Boom(FakeClient):
        def _create(self, **kwargs):
            raise RuntimeError("llm down")

    with patch("webapp.assistant.get_db", return_value=db), pytest.raises(RuntimeError):
        send_message("owner@example.com", "all", None, "hi", MagicMock(), MagicMock(), client=Boom(_reply("x")))
    coll.insert_one.assert_not_called()
    coll.update_one.assert_not_called()


def test_send_message_on_existing_thread_uses_stored_profile_and_is_user_scoped():
    db, coll = _threads_db()
    oid = ObjectId()
    coll.find_one.return_value = {
        "_id": oid, "user_email": "owner@example.com", "profile_id": "stored", "title": "T",
        "messages": [{"role": "user", "content": "earlier", "at": "x"}, {"role": "assistant", "content": "a", "at": "x"}],
    }
    load = MagicMock(return_value=RECORDS)
    client = FakeClient(_reply(tool_calls=[_tool_call("cash_flow_summary", {})]), _reply(content="Follow-up"))
    with patch("webapp.assistant.get_db", return_value=db):
        out = send_message("owner@example.com", "other", str(oid), "and before?", load, MagicMock(), client=client)
    assert coll.find_one.call_args.args[0] == {"_id": oid, "user_email": "owner@example.com"}
    assert load.call_args.args[2] == "stored"
    assert [m["content"] for m in client.calls[0]["messages"][1:3]] == ["earlier", "a"]
    filt, update = coll.update_one.call_args.args
    assert filt == {"_id": oid, "user_email": "owner@example.com"}
    assert [m["content"] for m in update["$push"]["messages"]["$each"]] == ["and before?", "Follow-up"]
    assert out["thread"]["title"] == "T"


def test_send_message_unknown_or_foreign_thread_is_not_found():
    db, coll = _threads_db()
    coll.find_one.return_value = None
    with patch("webapp.assistant.get_db", return_value=db):
        for tid in (str(ObjectId()), "not-an-object-id"):
            with pytest.raises(ThreadNotFound):
                send_message("owner@example.com", "all", tid, "hi", MagicMock(), MagicMock(), client=FakeClient(_reply("x")))


def test_module_imports_neither_pandas_nor_openai():
    src = open(assistant.__file__).read()
    top = [line for line in src.splitlines() if line.startswith(("import ", "from "))]
    assert not any("pandas" in line or "openai" in line for line in top)


def test_run_turn_strips_markdown_bold_since_replies_render_as_plain_text():
    client = FakeClient(_reply(content="Your net worth is **$58,000**."))
    assert run_turn(client, [], "q", _ctx()[0]) == "Your net worth is $58,000."


# ── thread list / get / delete ───────────────────────────────────────────────


def test_list_threads_is_user_scoped_newest_first_and_capped():
    db, coll = _threads_db()
    oid = ObjectId()
    cursor = coll.find.return_value.sort.return_value.limit
    cursor.return_value = [{"_id": oid, "title": "Q", "updated_at": "2026-10-12"}]
    with patch("webapp.assistant.get_db", return_value=db):
        out = list_threads("owner@example.com")
    assert coll.find.call_args.args[0] == {"user_email": "owner@example.com"}
    assert "messages" not in coll.find.call_args.args[1]
    assert coll.find.return_value.sort.call_args.args == ("updated_at", -1)
    assert cursor.call_args.args == (50,)
    assert out == [{"id": str(oid), "title": "Q", "updated_at": "2026-10-12"}]


def test_get_thread_returns_messages_for_the_owner_only():
    db, coll = _threads_db()
    oid = ObjectId()
    coll.find_one.return_value = {"_id": oid, "user_email": "owner@example.com", "profile_id": "p1", "title": "Q",
                                  "messages": [{"role": "user", "content": "Q", "at": "t"}], "updated_at": "t"}
    with patch("webapp.assistant.get_db", return_value=db):
        out = get_thread("owner@example.com", str(oid))
    assert coll.find_one.call_args.args[0] == {"_id": oid, "user_email": "owner@example.com"}
    assert out == {"id": str(oid), "title": "Q", "profile_id": "p1", "updated_at": "t",
                   "messages": [{"role": "user", "content": "Q", "at": "t"}]}
    assert "user_email" not in out


def test_get_and_delete_unknown_thread_raise_not_found():
    db, coll = _threads_db()
    coll.find_one.return_value = None
    coll.delete_one.return_value.deleted_count = 0
    with patch("webapp.assistant.get_db", return_value=db):
        for call in (get_thread, delete_thread):
            for tid in (str(ObjectId()), "bad-id"):
                with pytest.raises(ThreadNotFound):
                    call("owner@example.com", tid)


def test_delete_thread_is_user_scoped():
    db, coll = _threads_db()
    oid = ObjectId()
    coll.delete_one.return_value.deleted_count = 1
    with patch("webapp.assistant.get_db", return_value=db):
        delete_thread("owner@example.com", str(oid))
    assert coll.delete_one.call_args.args[0] == {"_id": oid, "user_email": "owner@example.com"}


def test_is_configured_follows_the_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert is_configured() is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    assert is_configured() is True
