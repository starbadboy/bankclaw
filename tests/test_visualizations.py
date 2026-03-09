import pandas as pd
import pytest
import runpy
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from webapp.visualizations_helpers import compute_monthly_cash_flow, compute_category_expenses


def make_df():
    return pd.DataFrame([
        {"date": "2024-01-10", "description": "SALARY",    "amount": 5000.00, "bank": "DBS", "category": "Income"},
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount":  -12.50, "bank": "DBS", "category": "Transport"},
        {"date": "2024-01-20", "description": "NTUC",      "amount":  -80.00, "bank": "DBS", "category": "Food & Dining"},
        {"date": "2024-02-05", "description": "FREELANCE", "amount":  800.00, "bank": "DBS", "category": "Income"},
        {"date": "2024-02-18", "description": "NETFLIX",   "amount":  -18.00, "bank": "DBS", "category": "Entertainment"},
    ])


def make_category_detail_df():
    rows = [
        {"date": "2024-01-01", "description": "SALARY", "amount": 5000.00, "bank": "DBS", "category": "Income"},
        {"date": "2024-01-02", "description": "REFUND", "amount": 15.00, "bank": "DBS", "category": "Transport"},
        {"date": "2024-01-03", "description": "LUNCH", "amount": -25.00, "bank": "DBS", "category": "Food & Dining"},
    ]
    transport_amounts = [-5.0, -120.0, -12.5, -80.0, -60.0, -45.0, -33.0, -150.0, -22.0, -95.0, -41.0, -10.0]
    for index, amount in enumerate(transport_amounts, start=1):
        rows.append(
            {
                "date": f"2024-02-{index:02d}",
                "description": f"TRANSPORT {index}",
                "amount": amount,
                "bank": "DBS",
                "category": "Transport",
            }
        )
    return pd.DataFrame(rows)


def test_compute_monthly_cash_flow_income():
    df = make_df()
    result = compute_monthly_cash_flow(df)
    assert result.loc["2024-01-01", "Income"] == pytest.approx(5000.00)
    assert result.loc["2024-02-01", "Income"] == pytest.approx(800.00)


def test_compute_monthly_cash_flow_expenses():
    df = make_df()
    result = compute_monthly_cash_flow(df)
    assert result.loc["2024-01-01", "Expenses"] == pytest.approx(92.50)
    assert result.loc["2024-02-01", "Expenses"] == pytest.approx(18.00)


def test_compute_monthly_cash_flow_net():
    df = make_df()
    result = compute_monthly_cash_flow(df)
    assert result.loc["2024-01-01", "Net"] == pytest.approx(4907.50)


def test_compute_category_expenses_excludes_positive_amounts():
    df = make_df()
    result = compute_category_expenses(df)
    assert "Income" not in result.index or result.get("Income", 0) == 0


def test_compute_category_expenses_sums_correctly():
    df = make_df()
    result = compute_category_expenses(df)
    assert result["Transport"] == pytest.approx(12.50)
    assert result["Food & Dining"] == pytest.approx(80.00)


def test_cash_flow_chart_uses_dark_dashboard_palette():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    monthly = compute_monthly_cash_flow(make_df())

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        plotly_chart_mock = MagicMock()
        module_globals["st"].plotly_chart = plotly_chart_mock
        module_globals["_show_cash_flow_chart"](monthly)

    chart = plotly_chart_mock.call_args.args[0]
    assert chart.layout.plot_bgcolor == "#09111f"
    assert chart.layout.paper_bgcolor == "#09111f"
    assert chart.layout.yaxis.gridcolor == "#1f3047"
    assert chart.data[2].line.color == "#7dd3fc"


def test_get_top_category_transactions_returns_top_10_negative_transactions_sorted_by_absolute_amount():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        result = module_globals["_get_top_category_transactions"](make_category_detail_df(), "Transport")

    assert list(result["description"]) == [
        "TRANSPORT 8",
        "TRANSPORT 2",
        "TRANSPORT 10",
        "TRANSPORT 4",
        "TRANSPORT 5",
        "TRANSPORT 6",
        "TRANSPORT 11",
        "TRANSPORT 7",
        "TRANSPORT 9",
        "TRANSPORT 3",
    ]
    assert list(result["amount"]) == [-150.0, -120.0, -95.0, -80.0, -60.0, -45.0, -41.0, -33.0, -22.0, -12.5]


def _columns_factory(spec):
    if isinstance(spec, int):
        return [MagicMock() for _ in range(spec)]
    if isinstance(spec, list):
        return [MagicMock() for _ in range(len(spec))]
    return [MagicMock(), MagicMock()]


def test_show_dashboard_renders_category_exclusion_multiselect():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]) as multiselect_mock, \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["show_mongodb_dashboard"](make_df())

    multiselect_mock.assert_called_once_with(
        "Exclude categories",
        options=["Food & Dining", "Entertainment", "Transport"],
        default=[],
        help="Hide selected categories from the Category Breakdown chart.",
        key="category_breakdown_excluded_categories",
    )


def test_show_dashboard_keeps_full_donut_when_no_categories_are_excluded():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]) as plotly_events_mock, \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["show_mongodb_dashboard"](make_df())

    donut_fig = plotly_events_mock.call_args.args[0]
    assert list(donut_fig.data[0].labels) == ["Food & Dining", "Entertainment", "Transport"]
    assert list(donut_fig.data[0].values) == [80.0, 18.0, 12.5]
    donut_json = donut_fig.to_json()
    assert '"values":[80.0,18.0,12.5]' in donut_json
    assert '"dtype"' not in donut_json


def test_show_dashboard_filters_excluded_categories_from_donut_chart():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=["Food & Dining"]), \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]) as plotly_events_mock, \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["show_mongodb_dashboard"](make_df())

    donut_fig = plotly_events_mock.call_args.args[0]
    assert list(donut_fig.data[0].labels) == ["Entertainment", "Transport"]
    assert list(donut_fig.data[0].values) == [18.0, 12.5]


def test_show_dashboard_shows_empty_state_when_all_categories_are_excluded():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=["Food & Dining", "Entertainment", "Transport"]), \
         patch("streamlit.info") as info_mock, \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events") as plotly_events_mock, \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        info_mock.reset_mock()
        plotly_events_mock.reset_mock()
        module_globals["show_mongodb_dashboard"](make_df())

    info_mock.assert_called_once_with("No categories left to display. Clear one or more exclusions.")
    assert plotly_events_mock.call_args_list == []


def test_show_dashboard_does_not_render_category_detail_panel_before_selection():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    columns_mock = MagicMock(side_effect=_columns_factory)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", columns_mock), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.rerun") as rerun_mock, \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]) as plotly_events_mock, \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["st"].session_state = {}
        module_globals["show_mongodb_dashboard"](make_category_detail_df())

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert "Top 10 Transactions" not in rendered
    assert plotly_events_mock.call_count == 1
    assert plotly_events_mock.call_args.kwargs["click_event"] is True
    assert plotly_events_mock.call_args.kwargs["hover_event"] is True
    assert plotly_events_mock.call_args.kwargs["key"] == "category_breakdown_chart"
    assert [3, 2] not in [call.args[0] for call in columns_mock.call_args_list]
    rerun_mock.assert_not_called()


def test_show_dashboard_hover_updates_selected_category_and_requests_rerun():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.rerun") as rerun_mock, \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[{"pointNumber": 0}]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["st"].session_state = {}
        module_globals["show_mongodb_dashboard"](make_category_detail_df())

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert "Top 10 Transactions in Transport" not in rendered
    assert module_globals["st"].session_state["category_breakdown_selected_category"] == "Transport"
    rerun_mock.assert_called_once()


def test_show_dashboard_keeps_category_detail_panel_when_no_new_hover_event():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.rerun") as rerun_mock, \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["st"].session_state = {"category_breakdown_selected_category": "Transport"}
        module_globals["show_mongodb_dashboard"](make_category_detail_df())

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert "Top 10 Transactions in Transport" in rendered
    assert "TRANSPORT 8" in rendered
    assert "TRANSPORT 12" not in rendered
    rerun_mock.assert_not_called()


def test_show_dashboard_escapes_html_sensitive_panel_content():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    sensitive_df = pd.DataFrame([
        {
            "date": "2024-03-01",
            "description": "<b>unsafe & cafe</b>",
            "amount": -42.0,
            "bank": "DBS <Main> & Co",
            "category": "Food <Fun> & Dining",
        }
    ])

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.rerun"), \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["st"].session_state = {"category_breakdown_selected_category": "Food <Fun> & Dining"}
        module_globals["show_mongodb_dashboard"](sensitive_df)

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert "Top 10 Transactions in Food &lt;Fun&gt; &amp; Dining" in rendered
    assert "&lt;b&gt;unsafe &amp; cafe&lt;/b&gt;" in rendered
    assert "DBS &lt;Main&gt; &amp; Co" in rendered
    assert "Top 10 Transactions in Food <Fun> & Dining" not in rendered
    assert "<b>unsafe & cafe</b>" not in rendered
    assert "DBS <Main> & Co" not in rendered


def test_show_dashboard_does_not_indent_detail_rows_as_literal_html_blocks():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.rerun"), \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["st"].session_state = {"category_breakdown_selected_category": "Transport"}
        module_globals["show_mongodb_dashboard"](make_category_detail_df())

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert '\n            <div class="category-detail-item">' not in rendered
    assert '\n                <div class="category-detail-item-description">' not in rendered


def test_visualizations_page_renders_modern_workspace_shell():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        runpy.run_path(str(page_path))

    rendered = " ".join(call.args[0] for call in mock_markdown.call_args_list if call.args)
    assert "Insights Workspace" in rendered
    assert '<div class="viz-toolbar-shell' in rendered
    assert '<section class="viz-shell' in rendered


def test_visualizations_page_renders_structured_analytics_sections():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.plotly_chart"), \
         patch("streamlit_plotly_events.plotly_events", return_value=[]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=make_df()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["show_mongodb_dashboard"](make_df())

    rendered = " ".join(call.args[0] for call in mock_markdown.call_args_list if call.args)
    assert '<div class="insights-section-shell">' in rendered
    assert "Primary Trend" in rendered
    assert '<div class="insights-chart-shell">' in rendered


def test_visualizations_page_uses_last_year_default_and_shows_upload_cta_when_empty():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    fixed_today = date.today()
    expected_start = fixed_today - timedelta(days=365)

    mock_date_input = MagicMock(side_effect=[expected_start, fixed_today])
    mock_button = MagicMock(return_value=False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", mock_date_input), \
         patch("streamlit.button", mock_button), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        runpy.run_path(str(page_path))

    from_call = mock_date_input.call_args_list[0]
    to_call = mock_date_input.call_args_list[1]
    assert from_call.kwargs["value"] == expected_start
    assert to_call.kwargs["value"] == fixed_today
    mock_button.assert_any_call("Upload Statement PDF", type="primary")
    mock_button.assert_any_call("Apply Date Filter", type="primary")


def test_upload_dialog_shows_supported_banks_thumbnail():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    expander_cm = MagicMock()
    expander_cm.__enter__.return_value = MagicMock()
    expander_cm.__exit__.return_value = False

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.expander", return_value=expander_cm), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["_render_supported_banks_thumbnail"]()

    rendered = " ".join(call.args[0] for call in mock_markdown.call_args_list if call.args)
    assert "Supported Banks" in rendered
    assert "DBS/POSB" in rendered


def test_visualizations_page_shows_upload_button_even_when_data_exists():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    mock_button = MagicMock(return_value=False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", mock_button), \
         patch("streamlit.plotly_chart"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=make_df()):
        runpy.run_path(str(page_path))

    mock_button.assert_any_call("Upload Statement PDF", type="primary")


def test_upload_dialog_process_does_not_save_directly_before_review():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    raw_df = pd.DataFrame([{"date": "2024-01-10", "description": "Salary", "amount": 5000.0, "bank": "DBS"}])
    categorized_df = raw_df.assign(category=["Income"])

    mock_button = MagicMock(return_value=False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.file_uploader", return_value=[MagicMock()]), \
         patch("streamlit.button", mock_button):
        module_globals = runpy.run_path(str(page_path))
        dialog_fn = module_globals["_show_upload_dialog"]
        dialog_fn.__globals__["st"].session_state = {}
        dialog_fn.__globals__["st"].button = MagicMock(side_effect=[True, False])
        dialog_fn.__globals__["process_files"] = MagicMock(return_value=[MagicMock()])
        dialog_fn.__globals__["create_df"] = MagicMock(return_value=raw_df)
        dialog_fn.__globals__["categorize_transactions"] = MagicMock(return_value=categorized_df)
        save_mock = MagicMock()
        dialog_fn.__globals__["save_transactions"] = save_mock
        dialog_fn("user@example.com")

    save_mock.assert_not_called()


def test_maybe_open_upload_dialog_reopens_when_flag_true():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.expander"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        maybe_open = module_globals["_maybe_open_upload_dialog"]
        st_obj = module_globals["st"]
        dialog_fn_spy = MagicMock()
        maybe_open.__globals__["_show_upload_dialog"] = dialog_fn_spy
        st_obj.session_state = {"viz_upload_dialog_open": True}

        maybe_open("user@example.com")

    dialog_fn_spy.assert_called_once_with("user@example.com")


def test_open_upload_dialog_sets_flag_without_opening_dialog_directly():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        open_fn = module_globals["_open_upload_dialog"]
        st_obj = open_fn.__globals__["st"]
        dialog_fn_spy = MagicMock()
        open_fn.__globals__["_show_upload_dialog"] = dialog_fn_spy
        st_obj.session_state = {}

        open_fn()

    assert st_obj.session_state["viz_upload_dialog_open"] is True
    dialog_fn_spy.assert_not_called()


def test_upload_review_table_converts_date_to_string():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    review_df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-03-01"),
            "description": "TEST",
            "amount": 1.23,
            "bank": "DBS",
            "category": "Other",
        }
    ])

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        dialog_fn = module_globals["_show_upload_dialog"]
        st_obj = dialog_fn.__globals__["st"]
        st_obj.session_state = {"viz_upload_review_df": review_df}
        st_obj.data_editor = MagicMock(return_value=review_df)

        dialog_fn("user@example.com")

    rendered_df = st_obj.data_editor.call_args.args[0]
    assert rendered_df.loc[0, "date"] == "2026-03-01"


def test_upload_dialog_ai_process_shows_spinner_beside_action_button():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    raw_df = pd.DataFrame([{"date": "2024-01-10", "description": "Salary", "amount": 5000.0, "bank": "DBS"}])
    categorized_df = raw_df.assign(category=["Income"])

    spinner_cm = MagicMock()
    spinner_cm.__enter__.return_value = None
    spinner_cm.__exit__.return_value = False

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.file_uploader", return_value=[MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.spinner", return_value=spinner_cm) as spinner_mock, \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        dialog_fn = module_globals["_show_upload_dialog"]
        dialog_fn.__globals__["st"].session_state = {}
        dialog_fn.__globals__["st"].button = MagicMock(side_effect=[True, False])
        dialog_fn.__globals__["process_files"] = MagicMock(return_value=[MagicMock()])
        dialog_fn.__globals__["create_df"] = MagicMock(return_value=raw_df)
        dialog_fn.__globals__["categorize_transactions"] = MagicMock(return_value=categorized_df)
        dialog_fn("user@example.com")

    spinner_mock.assert_called_once_with("Analyzing with AI...")


def test_upload_dialog_process_passes_user_email_to_categorizer():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    raw_df = pd.DataFrame([{"date": "2024-01-10", "description": "Salary", "amount": 5000.0, "bank": "DBS"}])
    categorized_df = raw_df.assign(category=["Income"])

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.file_uploader", return_value=[MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        dialog_fn = module_globals["_show_upload_dialog"]
        dialog_fn.__globals__["st"].session_state = {}
        dialog_fn.__globals__["st"].button = MagicMock(side_effect=[True, False])
        dialog_fn.__globals__["process_files"] = MagicMock(return_value=[MagicMock()])
        dialog_fn.__globals__["create_df"] = MagicMock(return_value=raw_df)
        categorize_mock = MagicMock(return_value=categorized_df)
        dialog_fn.__globals__["categorize_transactions"] = categorize_mock
        dialog_fn("demo@example.com")

    categorize_mock.assert_called_once_with(raw_df, user_email="demo@example.com")


def test_upload_review_save_persists_only_manual_category_changes_to_memory():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    review_df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-03-01"),
            "description": "GRAB TAXI",
            "amount": -12.5,
            "bank": "DBS",
            "category": "Transport",
        },
        {
            "date": pd.Timestamp("2026-03-02"),
            "description": "NTUC",
            "amount": -22.0,
            "bank": "DBS",
            "category": "Food & Dining",
        },
    ])
    edited_df = review_df.copy()
    edited_df.loc[0, "category"] = "Other"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.rerun"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        dialog_fn = module_globals["_show_upload_dialog"]
        st_obj = dialog_fn.__globals__["st"]
        st_obj.session_state = {"viz_upload_review_df": review_df}
        st_obj.data_editor = MagicMock(return_value=edited_df)
        save_transactions_mock = MagicMock(return_value=2)
        save_memory_mock = MagicMock(return_value=1)
        dialog_fn.__globals__["save_transactions"] = save_transactions_mock
        dialog_fn.__globals__["save_category_memory"] = save_memory_mock
        dialog_fn.__globals__["st"].button = MagicMock(side_effect=[True, False])

        dialog_fn("demo@example.com")

    save_transactions_mock.assert_called_once()
    save_memory_mock.assert_called_once()
    saved_memory_df = save_memory_mock.call_args.args[0]
    assert len(saved_memory_df) == 1
    assert saved_memory_df.iloc[0]["description"] == "GRAB TAXI"
    assert saved_memory_df.iloc[0]["category"] == "Other"
    assert save_memory_mock.call_args.kwargs["user_email"] == "demo@example.com"
    assert save_memory_mock.call_args.kwargs["source"] == "manual"


def test_upload_review_save_warns_when_memory_update_fails():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    review_df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-03-01"),
            "description": "GRAB TAXI",
            "amount": -12.5,
            "bank": "DBS",
            "category": "Transport",
        }
    ])
    edited_df = review_df.copy()
    edited_df.loc[0, "category"] = "Other"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.dialog", lambda *args, **kwargs: (lambda func: func)), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.rerun"), \
         patch("streamlit.warning") as warning_mock, \
         patch("streamlit.success") as success_mock, \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        dialog_fn = module_globals["_show_upload_dialog"]
        st_obj = dialog_fn.__globals__["st"]
        st_obj.session_state = {"viz_upload_review_df": review_df}
        st_obj.data_editor = MagicMock(return_value=edited_df)
        dialog_fn.__globals__["save_transactions"] = MagicMock(return_value=1)
        dialog_fn.__globals__["save_category_memory"] = MagicMock(side_effect=RuntimeError("memory unavailable"))
        dialog_fn.__globals__["st"].button = MagicMock(side_effect=[True, False])

        dialog_fn("demo@example.com")

    warning_mock.assert_called_once()
    success_mock.assert_called_once()
