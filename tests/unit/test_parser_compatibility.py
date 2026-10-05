from dataclasses import dataclass
from unittest.mock import patch

from webapp.helpers import create_df
from webapp.models import ProcessedFile, TransactionMetadata


def test_dataframe_accepts_new_parser_fields_and_excludes_metadata():
    @dataclass
    class Transaction:
        date: str
        description: str
        amount: float
        direction: str
        balance: float | None
        currency: str

    file = ProcessedFile(
        [Transaction("2024-01-15", "GROCERIES", -45.3, "debit", None, "SGD")],
        TransactionMetadata("DBS"),
    )
    with patch("webapp.helpers.st"):
        df = create_df([file])
    assert df.columns.tolist() == ["date", "description", "amount", "bank"]
    assert df.iloc[0]["amount"] == -45.3
    assert df.iloc[0]["bank"] == "DBS"
    assert str(df.iloc[0]["date"]) == "2024-01-15"
