import runpy
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd


def test_history_page_renders_workspace_header_and_filter_shell():
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
    assert '<section class="history-shell">' in rendered
    assert "Transaction History Workspace" in rendered
    assert '<div class="history-filter-shell">' in rendered


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


def test_history_page_persists_manual_category_changes_to_memory():
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
         patch("webapp.repository.save_category_memory") as mock_save_memory, \
         patch("webapp.repository.delete_transactions") as mock_delete, \
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

    mock_save.assert_called_once()
    mock_save_memory.assert_called_once()
    saved_memory_df = mock_save_memory.call_args.args[0]
    assert len(saved_memory_df) == 1
    assert saved_memory_df.iloc[0]["description"] == "Coffee"
    assert saved_memory_df.iloc[0]["category"] == "Other"
    assert mock_save_memory.call_args.kwargs["user_email"] == "demo@example.com"
    assert mock_save_memory.call_args.kwargs["source"] == "manual"
    mock_delete.assert_not_called()


def test_history_page_skips_category_memory_for_rows_pending_delete():
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
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("webapp.repository.save_category_memory") as mock_save_memory, \
         patch("webapp.repository.delete_transactions") as mock_delete, \
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

    mock_save.assert_not_called()
    mock_save_memory.assert_not_called()
    mock_delete.assert_not_called()


def test_history_page_warns_when_memory_update_fails():
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
         patch("webapp.repository.save_category_memory", side_effect=RuntimeError("memory unavailable")), \
         patch("webapp.repository.delete_transactions") as mock_delete, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df), \
         patch("streamlit.download_button"), \
         patch("streamlit.warning") as warning_mock, \
         patch("streamlit.success") as success_mock, \
         patch("streamlit.rerun"), \
         patch("streamlit.button", side_effect=_button_side_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_save.assert_called_once()
    warning_mock.assert_called_once()
    success_mock.assert_called_once()
    mock_delete.assert_not_called()


def test_history_page_cancel_delete_preserves_category_edit():
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
    edited_df["_delete"] = True

    def _button_side_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        mapping = {
            "Logout": False,
            "🔍 Load Transactions": True,
            "Confirm Delete": False,
            "Cancel": True,
        }
        return mapping.get(label, False)

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("webapp.repository.save_category_memory") as mock_save_memory, \
         patch("webapp.repository.delete_transactions") as mock_delete, \
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

    mock_save.assert_called_once()
    mock_save_memory.assert_called_once()
    mock_delete.assert_not_called()


def test_history_page_shows_legacy_categories_read_only_and_keeps_editor_options_active_only():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Legacy Merchant",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Archived Category",
            "saved_at": "2026-03-01T01:00:00Z",
        }
    ])
    edited_df = loaded_df.copy()
    edited_df["_delete"] = False

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.category_definitions.get_effective_categories", return_value=["Food & Dining", "Pet Care", "Other"]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("webapp.repository.save_transactions") as mock_save, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.column_config.SelectboxColumn") as mock_selectbox_column, \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df) as mock_editor, \
         patch("streamlit.dataframe") as mock_dataframe, \
         patch("streamlit.download_button"), \
         patch("streamlit.warning") as mock_warning, \
         patch("streamlit.button", side_effect=lambda label, *args, **kwargs: label == "🔍 Load Transactions"):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_editor.assert_not_called()
    mock_dataframe.assert_called_once()
    mock_save.assert_not_called()
    assert mock_selectbox_column.call_count == 0
    mock_warning.assert_called_once()
    assert "Archived Category" in mock_warning.call_args.args[0]


def test_history_page_falls_back_to_default_categories_when_dynamic_lookup_fails():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Coffee",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Pet Care",
            "saved_at": "2026-03-01T01:00:00Z",
        }
    ])
    edited_df = loaded_df.copy()
    edited_df["_delete"] = False

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.category_definitions.get_effective_categories", side_effect=RuntimeError("lookup failed")), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.column_config.SelectboxColumn") as mock_selectbox_column, \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df) as mock_editor, \
         patch("streamlit.dataframe") as mock_dataframe, \
         patch("streamlit.download_button") as mock_download, \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.warning") as mock_warning, \
         patch("streamlit.button", side_effect=lambda label, *args, **kwargs: label == "🔍 Load Transactions"):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_error.assert_called_once()
    mock_warning.assert_called_once()
    mock_editor.assert_not_called()
    mock_dataframe.assert_called_once()
    mock_download.assert_called_once()
    assert mock_selectbox_column.call_count == 0


def test_history_page_keeps_active_rows_editable_while_legacy_rows_are_read_only():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    loaded_df = pd.DataFrame([
        {
            "date": "2026-03-01",
            "description": "Coffee",
            "amount": -5.5,
            "bank": "DBS",
            "category": "Food & Dining",
            "saved_at": "2026-03-01T01:00:00Z",
        },
        {
            "date": "2026-03-02",
            "description": "Legacy Merchant",
            "amount": -15.0,
            "bank": "DBS",
            "category": "Archived Category",
            "saved_at": "2026-03-02T01:00:00Z",
        },
    ])
    edited_df = loaded_df.iloc[[0]].copy()
    edited_df["_delete"] = False

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.category_definitions.get_effective_categories", return_value=["Food & Dining", "Pet Care", "Other"]), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=loaded_df), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.column_config.SelectboxColumn") as mock_selectbox_column, \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.selectbox", return_value="All"), \
         patch("streamlit.data_editor", return_value=edited_df) as mock_editor, \
         patch("streamlit.dataframe") as mock_dataframe, \
         patch("streamlit.download_button"), \
         patch("streamlit.warning") as mock_warning, \
         patch("streamlit.button", side_effect=lambda label, *args, **kwargs: label == "🔍 Load Transactions"):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_editor.assert_called_once()
    editor_df = mock_editor.call_args.args[0]
    assert len(editor_df) == 1
    assert list(editor_df["category"]) == ["Food & Dining"]
    mock_dataframe.assert_called_once()
    legacy_df = mock_dataframe.call_args.args[0]
    assert len(legacy_df) == 1
    assert list(legacy_df["category"]) == ["Archived Category"]
    assert "Archived Category" not in mock_selectbox_column.call_args.kwargs["options"]
    mock_warning.assert_called_once()


def _make_custom_category_df(names: list[str]) -> "pd.DataFrame":
    import pandas as pd  # noqa: PLC0415
    return pd.DataFrame([
        {
            "user_email": "demo@example.com",
            "name": name,
            "normalized_name": name.lower(),
            "is_active": True,
            "created_at": "2026-03-01T00:00:00Z",
            "updated_at": "2026-03-01T00:00:00Z",
        }
        for name in names
    ])


def test_category_manager_renders_active_custom_categories():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    custom_cats_df = _make_custom_category_df(["Pet Care", "Gym"])

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_custom_categories", return_value=custom_cats_df) as mock_get, \
         patch("webapp.repository.save_custom_category"), \
         patch("webapp.repository.archive_custom_category"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander") as mock_expander, \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.text_input", return_value=""), \
         patch("streamlit.button", return_value=False):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_get.assert_any_call("demo@example.com")
    assert mock_expander.called


def test_category_manager_add_category_calls_save():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    custom_cats_df = _make_custom_category_df([])

    def _button_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return label == "Add Category"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_custom_categories", return_value=custom_cats_df), \
         patch("webapp.repository.save_custom_category") as mock_save, \
         patch("webapp.repository.archive_custom_category"), \
         patch("webapp.category_definitions.validate_custom_category_name", return_value="Pet Care"), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.text_input", return_value="Pet Care"), \
         patch("streamlit.success"), \
         patch("streamlit.rerun"), \
         patch("streamlit.button", side_effect=_button_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_save.assert_called_once_with("Pet Care", "demo@example.com")


def test_category_manager_archive_category_calls_archive():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    custom_cats_df = _make_custom_category_df(["Pet Care"])

    def _button_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return label == "Archive" and kwargs.get("key", "").endswith("Pet Care")

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_custom_categories", return_value=custom_cats_df), \
         patch("webapp.repository.save_custom_category"), \
         patch("webapp.repository.archive_custom_category") as mock_archive, \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.text_input", return_value=""), \
         patch("streamlit.success"), \
         patch("streamlit.rerun"), \
         patch("streamlit.button", side_effect=_button_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_archive.assert_called_once_with("Pet Care", "demo@example.com")


def test_category_manager_invalid_name_shows_error():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "3_history.py"
    custom_cats_df = _make_custom_category_df([])

    def _button_effect(label, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return label == "Add Category"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("webapp.repository.get_custom_categories", return_value=custom_cats_df), \
         patch("webapp.repository.save_custom_category") as mock_save, \
         patch("webapp.repository.archive_custom_category"), \
         patch("webapp.category_definitions.validate_custom_category_name", side_effect=ValueError("Category name already exists")), \
         patch("streamlit.markdown"), \
         patch("streamlit.caption"), \
         patch("streamlit.expander", return_value=MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))), \
         patch("streamlit.columns", return_value=[MagicMock(), MagicMock()]), \
         patch("streamlit.date_input", side_effect=[date(2026, 3, 1), date(2026, 3, 5)]), \
         patch("streamlit.text_input", return_value="Food & Dining"), \
         patch("streamlit.error") as mock_error, \
         patch("streamlit.button", side_effect=_button_effect):
        module_globals = runpy.run_path(str(page_path))
        module_globals["history_page"]()

    mock_save.assert_not_called()
    mock_error.assert_called_once()
    assert "already exists" in mock_error.call_args.args[0]
