import runpy
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd


def test_history_page_removes_workspace_header_and_filter_box():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    rendered = " ".join(call.args[0] for call in mock_markdown.call_args_list if call.args)
    assert "Transaction History Workspace" not in rendered
    assert "history-filter-shell" not in rendered


def test_history_page_auto_saves_category_changes_without_button():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Coffee",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Food & Dining",
            "saved_at": "2026-03-01T01:00:00Z",
        }
    ])
    edited_df = loaded_df.copy()
    edited_df.loc[0, "category"] = "Other"
    edited_df["_delete"] = False

    def _button_side_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        mapping = {
            "Logout": False,
            "🔍 Load Transactions": True,
        }
        return mapping.get(label, False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("webapp.repository.delete_transactions") as mock_delete, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df) as mock_editor, \
         patch("streamlit.download_button"), \
         patch("streamlit.rerun"), \
         patch("streamlit.button", side_effect=_button_side_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_editor.assert_called_once()
    mock_save.assert_called_once()
    mock_delete.assert_not_called()


def test_history_page_deletes_row_only_after_confirm_delete_click():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Coffee",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Food & Dining",
            "saved_at": "2026-03-01T01:00:00Z",
        }
    ])
    edited_df = loaded_df.copy()
    edited_df["_delete"] = True

    def _button_side_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        mapping = {
            "Logout": False,
            "🔍 Load Transactions": True,
            "Confirm Delete": True,
            "Cancel": False,
        }
        return mapping.get(label, False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("webapp.repository.delete_transactions") as mock_delete, \
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df), \
         patch("streamlit.download_button"), \
         patch("streamlit.rerun"), \
         patch("streamlit.button", side_effect=_button_side_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_delete.assert_called_once()
    mock_save.assert_not_called()


def test_history_page_shows_delete_confirmation_before_deleting():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Coffee",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Food & Dining",
            "saved_at": "2026-03-01T01:00:00Z",
        }
    ])
    edited_df = loaded_df.copy()
    edited_df["_delete"] = True

    def _button_side_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        mapping = {
            "Logout": False,
            "🔍 Load Transactions": True,
            "Confirm Delete": False,
            "Cancel": False,
        }
        return mapping.get(label, False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("webapp.repository.delete_transactions") as mock_delete, \
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.warning") as mock_warning, \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df), \
         patch("streamlit.download_button"), \
         patch("streamlit.rerun"), \
         patch("streamlit.button", side_effect=_button_side_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_warning.assert_called_once()
    mock_delete.assert_not_called()
    mock_save.assert_not_called()


def test_history_page_handles_missing_trash_column_without_keyerror():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Coffee",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Food & Dining",
            "saved_at": "2026-03-01T01:00:00Z",
        }
    ])

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("webapp.repository.delete_transactions") as mock_delete, \
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=loaded_df), \
         patch("streamlit.download_button"), \
         patch("streamlit.button", side_effect=lambda label, *args, **kwargs: label == "🔍 Load Transactions"):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_delete.assert_not_called()
    mock_save.assert_not_called()
