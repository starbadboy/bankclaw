import pandas as pd


def compute_monthly_cash_flow(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.index = pd.to_datetime(df["date"])
    df["Income"] = df["amount"].apply(lambda x: max(0.0, x))
    df["Expenses"] = df["amount"].apply(lambda x: abs(x) if x < 0 else 0.0)
    df["Net"] = df["amount"]
    return df.resample("MS")[["Income", "Expenses", "Net"]].sum()


def compute_category_expenses(df: pd.DataFrame) -> pd.Series:
    expenses = df[df["amount"] < 0].copy()
    expenses["amount_abs"] = expenses["amount"].abs()
    return expenses.groupby("category")["amount_abs"].sum().sort_values(ascending=False)
