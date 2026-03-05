from unittest.mock import MagicMock, patch

import pandas as pd

from webapp.app import app


def test_anonymous_user_sees_auth_screen_instead_of_uploader():
    mock_st = MagicMock()
    mock_st.session_state = {"auth_user": None}

    with patch("webapp.app.st", mock_st), patch("webapp.app._show_auth_screen"), patch("webapp.app.get_files") as get_files:
        app()

    get_files.assert_not_called()


def test_logged_in_user_can_save_transactions_under_own_identity():
    categorized_df = pd.DataFrame([
        {
            "date": "2024-01-10",
            "description": "Salary",
            "amount": 5000.0,
            "bank": "DBS",
            "category": "Income",
        }
    ])
    mock_st = MagicMock()
    mock_st.session_state = {"auth_user": {"email": "user@example.com"}}
    mock_st.data_editor.return_value = categorized_df
    mock_st.columns.return_value = [MagicMock(), MagicMock()]
    mock_st.button.side_effect = [True, False]

    with patch("webapp.app.st", mock_st), patch("webapp.app.save_transactions", return_value=1) as save_mock:
        from webapp.app import _show_review_and_save

        _show_review_and_save(categorized_df)

    _, kwargs = save_mock.call_args
    assert kwargs["user_email"] == "user@example.com"
