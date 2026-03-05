# pylint: disable=no-name-in-module
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
from streamlit.proto.Common_pb2 import FileURLs
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec

from webapp.app import app


def create_uploaded_file(file_name):
    with open(f"tests/fixtures/{file_name}", "rb") as f:
        raw_file = f.read()

    file_id = str(uuid4())

    record = UploadedFileRec(file_id=file_id, name=file_name, type="application/pdf", data=raw_file)
    upload_url = f"/_stcore/upload_file/{uuid4()}/{file_id}"
    file_urls = FileURLs(upload_url=upload_url, delete_url=upload_url)

    return UploadedFile(record, file_urls)


@pytest.fixture()
def uploaded_file():
    return create_uploaded_file("example_statement.pdf")


@pytest.fixture()
def protected_file():
    return create_uploaded_file("protected_example_statement.pdf")


def test_app(uploaded_file):
    with patch("webapp.app.get_files") as get_files, patch("webapp.app.is_authenticated", return_value=True):
        get_files.return_value = [uploaded_file]
        df = app()

    expected_df = pd.read_csv("tests/fixtures/example_statement.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df[["description", "amount", "date", "bank"]]
    expected_df["date"] = pd.to_datetime(expected_df["date"])
    assert df.equals(expected_df)


def test_unlock_protected(protected_file):
    os.environ["PDF_PASSWORDS"] = '["foobar123"]'
    with patch("webapp.app.get_files") as get_files, patch("webapp.app.is_authenticated", return_value=True):
        get_files.return_value = [protected_file]
        df = app()

    expected_df = pd.read_csv("tests/fixtures/example_statement.csv")

    df["date"] = pd.to_datetime(df["date"])
    df = df[["description", "amount", "date", "bank"]]
    expected_df["date"] = pd.to_datetime(expected_df["date"])

    assert df.equals(expected_df)


# ── helpers for new UI tests ──────────────────────────────────────────────────

def _make_raw_df():
    return pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC", "amount": -30.00, "bank": "DBS"},
    ])


def _make_categorized_df():
    df = _make_raw_df()
    df["category"] = ["Transport", "Food & Dining"]
    return df


def _make_mock_st(*, button_returns=None, columns=True):
    """Build a minimal st mock that supports spinner context manager and columns unpacking."""
    mock_st = MagicMock()
    if button_returns is not None:
        mock_st.button.side_effect = button_returns
    if columns:
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
    return mock_st


# ── _show_categorise_button ───────────────────────────────────────────────────

def test_categorise_button_calls_categorize_transactions():
    raw_df = _make_raw_df()
    cat_df = _make_categorized_df()

    mock_st = _make_mock_st(button_returns=[True])
    mock_st.session_state = {}

    with patch("webapp.app.st", mock_st), \
         patch("webapp.app.categorize_transactions", return_value=cat_df) as mock_cat:
        from webapp.app import _show_categorise_button
        _show_categorise_button(raw_df)

    mock_cat.assert_called_once()


def test_categorise_button_not_clicked_does_not_call_categorize():
    raw_df = _make_raw_df()

    mock_st = _make_mock_st(button_returns=[False])

    with patch("webapp.app.st", mock_st), \
         patch("webapp.app.categorize_transactions") as mock_cat:
        from webapp.app import _show_categorise_button
        _show_categorise_button(raw_df)

    mock_cat.assert_not_called()


# ── _show_review_and_save ─────────────────────────────────────────────────────

def test_review_and_save_calls_save_transactions_on_click():
    cat_df = _make_categorized_df()

    mock_st = _make_mock_st(button_returns=[True, False])
    mock_st.data_editor.return_value = cat_df

    with patch("webapp.app.st", mock_st), \
         patch("webapp.app.save_transactions", return_value=2) as mock_save:
        from webapp.app import _show_review_and_save
        _show_review_and_save(cat_df)

    mock_save.assert_called_once()


def test_review_and_save_does_not_save_when_not_clicked():
    cat_df = _make_categorized_df()

    mock_st = _make_mock_st(button_returns=[False, False])
    mock_st.data_editor.return_value = cat_df

    with patch("webapp.app.st", mock_st), \
         patch("webapp.app.save_transactions") as mock_save:
        from webapp.app import _show_review_and_save
        _show_review_and_save(cat_df)

    mock_save.assert_not_called()
