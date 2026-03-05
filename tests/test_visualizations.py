import pandas as pd
import pytest
from webapp.pages.visualizations_helpers import compute_monthly_cash_flow, compute_category_expenses


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
