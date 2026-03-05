from dataclasses import dataclass

from monopoly.statements import Transaction


@dataclass
class TransactionMetadata:
    bank_name: str


@dataclass
class ProcessedFile:
    transactions: list[Transaction]
    metadata: TransactionMetadata

    def __iter__(self):
        return iter(self.transactions)


@dataclass
class CategorizedTransaction:
    date: str
    description: str
    amount: float
    bank: str
    category: str
