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
    assert "insights-filter-shell" in rendered


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
    def columns_factory(spec):
        if isinstance(spec, int):
            return [MagicMock() for _ in range(spec)]
        if isinstance(spec, list):
            return [MagicMock() for _ in range(len(spec))]
        return [MagicMock(), MagicMock()]

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=columns_factory), \
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

        open_fn("user@example.com")

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
