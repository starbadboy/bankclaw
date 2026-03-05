from unittest.mock import patch

import pandas as pd

from webapp.helpers import categorize_and_save_df


def make_df():
    return pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
    ])


def test_categorize_and_save_df_returns_saved_count():
    df = make_df()
    categorized_df = df.assign(category=["Transport"])

    with patch("webapp.helpers.categorize_transactions", return_value=categorized_df) as mock_cat, patch(
        "webapp.helpers.save_transactions", return_value=1
    ) as mock_save:
        count = categorize_and_save_df(df)

    mock_cat.assert_called_once()
    mock_save.assert_called_once()
    assert count == 1


def test_categorize_and_save_df_passes_df_to_categorizer():
    df = make_df()
    categorized_df = df.assign(category=["Transport"])

    with patch("webapp.helpers.categorize_transactions", return_value=categorized_df) as mock_cat, patch(
        "webapp.helpers.save_transactions", return_value=1
    ):
        categorize_and_save_df(df)

    called_df = mock_cat.call_args[0][0]
    assert list(called_df.columns) == list(df.columns)
