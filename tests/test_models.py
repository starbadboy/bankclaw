from webapp.models import CategorizedTransaction


def test_categorized_transaction_fields():
    ct = CategorizedTransaction(
        date="2024-01-15",
        description="GRAB TAXI",
        amount=-12.50,
        bank="DBS",
        category="Transport",
    )
    assert ct.date == "2024-01-15"
    assert ct.description == "GRAB TAXI"
    assert ct.amount == -12.50
    assert ct.bank == "DBS"
    assert ct.category == "Transport"
