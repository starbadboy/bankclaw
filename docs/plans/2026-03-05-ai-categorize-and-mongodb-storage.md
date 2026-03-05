# AI Categorization + MongoDB Storage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** After converting a bank statement PDF to CSV, use DeepSeek AI to categorise each transaction and store the results in MongoDB Atlas, with a new Streamlit history page to browse saved records.

**Architecture:**
- `webapp/db.py` — MongoDB Atlas connection singleton using `pymongo`, configured via `MONGODB_URL` env var.
- `webapp/categorizer.py` — DeepSeek AI categorisation (OpenAI-compatible client) that batch-categorises all transactions in a single API call.
- `webapp/repository.py` — Upsert and query operations against the `transactions` MongoDB collection.
- `webapp/app.py` — "Save to MongoDB" button added below the CSV download button.
- `webapp/pages/3_history.py` — New Streamlit page to browse/filter saved transaction records.

**Tech Stack:** Python 3.12, Streamlit, pymongo 4.x, openai SDK (DeepSeek-compatible), MongoDB Atlas

**Status:** ✅ Complete — 14/14 tests passing, all 9 phases implemented.

---

## Requirements

### User Stories
- As a user, I want to click "Save to MongoDB" after parsing my PDFs so my transactions are stored permanently.
- As a user, I want each transaction to have an AI-assigned category (e.g. Food, Transport) so I can analyse my spending.
- As a user, I want to browse saved transactions by date range on a dedicated history page.

### Acceptance Criteria
- Given a parsed DataFrame, when I click "Save to MongoDB", then all transactions are upserted (no duplicates) with a `category` field.
- Given the history page, when I select a date range, then I see matching saved records from MongoDB.
- Given a missing `DEEPSEEK_API_KEY`, then the app shows a clear error and does not crash.
- Given a missing `MONGODB_URL`, then the app shows a clear error and does not crash.

---

## Architecture Changes

- Create: `webapp/db.py` — MongoDB connection singleton
- Create: `webapp/categorizer.py` — DeepSeek batch categorisation
- Create: `webapp/repository.py` — MongoDB transaction upsert + query
- Modify: `webapp/models.py` — add `CategorizedTransaction` dataclass
- Modify: `webapp/helpers.py` — add `categorize_and_save_df()` helper
- Modify: `webapp/app.py` — add "Save to MongoDB" button in `show_df` flow
- Create: `webapp/pages/3_history.py` — history browse page
- Modify: `pyproject.toml` — add `pymongo` and `openai` dependencies
- Create: `tests/test_categorizer.py` — unit tests (mock DeepSeek)
- Create: `tests/test_repository.py` — unit tests (mock pymongo)

> ⚠️ **DB NOTE:** This feature requires a MongoDB Atlas cluster and collection. No schema migration scripts are needed (MongoDB is schemaless), but you need an Atlas account + connection string set as `MONGODB_URL`. Collection `transactions` will be auto-created on first insert. Please ensure you have the `MONGODB_URL` and `DEEPSEEK_API_KEY` environment variables ready.

---

## MongoDB Document Schema

```json
{
  "_id": "<ObjectId>",
  "date": "2024-01-15",
  "description": "GRAB TAXI",
  "amount": -12.50,
  "bank": "DBS",
  "category": "Transport",
  "saved_at": "2024-01-20T10:00:00Z"
}
```

**Collection:** `transactions`
**Upsert key:** `{ date, description, amount, bank }` (prevents duplicates on re-upload)
**Index:** `{ date: 1 }` (for date-range queries — create manually in Atlas or on first connect)

**Categories (AI output constrained to these):**
`Food & Dining`, `Transport`, `Shopping`, `Entertainment`, `Utilities`, `Healthcare`, `Travel`, `Income`, `Transfer`, `Other`

---

## Implementation Steps

### Phase 1: Dependencies

#### Task 1: Add pymongo and openai to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependencies**

In `pyproject.toml`, under `dependencies`, add:
```toml
"pymongo>=4.9.0",
"openai>=1.0.0",
```

**Step 2: Install dependencies**

```bash
uv sync
```
Expected: packages installed without error.

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build(deps): add pymongo and openai for MongoDB + DeepSeek integration"
```

---

### Phase 2: MongoDB Connection

#### Task 2: Create `webapp/db.py`

**Files:**
- Create: `webapp/db.py`

**Step 1: Write the failing test**

Create `tests/test_db.py`:
```python
import os
from unittest.mock import MagicMock, patch

import pytest


def test_get_db_raises_when_no_url(monkeypatch):
    monkeypatch.delenv("MONGODB_URL", raising=False)
    # Re-import to reset module-level state
    import importlib
    import webapp.db as db_module
    importlib.reload(db_module)
    with pytest.raises(ValueError, match="MONGODB_URL"):
        db_module.get_db()


def test_get_db_returns_database(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/testdb")
    with patch("webapp.db.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        import importlib
        import webapp.db as db_module
        importlib.reload(db_module)
        db = db_module.get_db()
        assert db is not None
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```
Expected: FAIL with `ModuleNotFoundError` or similar (file doesn't exist yet).

**Step 3: Implement `webapp/db.py`**

```python
import os

from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None


def get_db() -> Database:
    url = os.getenv("MONGODB_URL")
    if not url:
        raise ValueError("MONGODB_URL environment variable is not set")

    global _client  # noqa: PLW0603
    if _client is None:
        _client = MongoClient(url)

    db_name = os.getenv("MONGODB_DB_NAME", "bankclaw")
    return _client[db_name]
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_db.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/db.py tests/test_db.py
git commit -m "feat: add MongoDB connection singleton in webapp/db.py"
```

---

### Phase 3: Data Model

#### Task 3: Add `CategorizedTransaction` to `webapp/models.py`

**Files:**
- Modify: `webapp/models.py`

**Step 1: Write the failing test**

Add to `tests/test_models.py` (create if not exists):
```python
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
    assert ct.category == "Transport"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```
Expected: FAIL with `ImportError: cannot import name 'CategorizedTransaction'`

**Step 3: Add `CategorizedTransaction` to `webapp/models.py`**

```python
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add webapp/models.py tests/test_models.py
git commit -m "feat: add CategorizedTransaction dataclass to models"
```

---

### Phase 4: AI Categorisation

#### Task 4: Create `webapp/categorizer.py`

**Files:**
- Create: `webapp/categorizer.py`
- Test: `tests/test_categorizer.py`

**Step 1: Write the failing test**

Create `tests/test_categorizer.py`:
```python
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from webapp.categorizer import categorize_transactions, VALID_CATEGORIES


def make_df():
    return pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
        {"date": "2024-01-16", "description": "NTUC FAIRPRICE", "amount": -45.30, "bank": "DBS"},
    ])


def test_categorize_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    df = make_df()
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        categorize_transactions(df)


def test_categorize_returns_df_with_category_column(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = make_df()

    mock_response_text = "Transport\nFood & Dining"
    mock_choice = MagicMock()
    mock_choice.message.content = mock_response_text
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df)

    assert "category" in result.columns
    assert list(result["category"]) == ["Transport", "Food & Dining"]


def test_invalid_category_falls_back_to_other(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    df = make_df()

    mock_response_text = "INVALID_CATEGORY\nFood & Dining"
    mock_choice = MagicMock()
    mock_choice.message.content = mock_response_text
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("webapp.categorizer.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        MockOpenAI.return_value = mock_client

        result = categorize_transactions(df)

    assert result.iloc[0]["category"] == "Other"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_categorizer.py -v
```
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement `webapp/categorizer.py`**

```python
import os

import pandas as pd
from openai import OpenAI

VALID_CATEGORIES = [
    "Food & Dining",
    "Transport",
    "Shopping",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Travel",
    "Income",
    "Transfer",
    "Other",
]

_SYSTEM_PROMPT = """You are a bank transaction categoriser. Given a list of bank transaction descriptions,
return exactly one category per line in the same order. Output ONLY the category names, one per line, nothing else.

Valid categories: {categories}
""".format(categories=", ".join(VALID_CATEGORIES))


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    descriptions = df["description"].tolist()
    user_content = "\n".join(
        f"{i + 1}. {desc}" for i, desc in enumerate(descriptions)
    )

    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
    )

    raw_lines = completion.choices[0].message.content.strip().splitlines()

    categories = []
    for line in raw_lines:
        line = line.strip()
        # Strip leading numbering like "1. " if model adds it
        if ". " in line:
            line = line.split(". ", 1)[-1].strip()
        categories.append(line if line in VALID_CATEGORIES else "Other")

    # Pad or truncate to match DataFrame length
    while len(categories) < len(df):
        categories.append("Other")
    categories = categories[: len(df)]

    result = df.copy()
    result["category"] = categories
    return result
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_categorizer.py -v
```
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add webapp/categorizer.py tests/test_categorizer.py
git commit -m "feat: add DeepSeek AI transaction categoriser"
```

---

### Phase 5: MongoDB Repository

#### Task 5: Create `webapp/repository.py`

**Files:**
- Create: `webapp/repository.py`
- Test: `tests/test_repository.py`

**Step 1: Write the failing test**

Create `tests/test_repository.py`:
```python
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from webapp.repository import save_transactions, get_transactions_by_date_range


def make_categorized_df():
    return pd.DataFrame([
        {
            "date": date(2024, 1, 15),
            "description": "GRAB TAXI",
            "amount": -12.50,
            "bank": "DBS",
            "category": "Transport",
        },
        {
            "date": date(2024, 1, 16),
            "description": "NTUC FAIRPRICE",
            "amount": -45.30,
            "bank": "DBS",
            "category": "Food & Dining",
        },
    ])


def test_save_transactions_upserts_records():
    df = make_categorized_df()
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    with patch("webapp.repository.get_db", return_value=mock_db):
        save_transactions(df)

    assert mock_collection.update_one.call_count == 2
    # Verify upsert=True was used
    call_kwargs = mock_collection.update_one.call_args_list[0][1]
    assert call_kwargs.get("upsert") is True


def test_get_transactions_by_date_range_returns_df():
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = [
        {
            "date": "2024-01-15",
            "description": "GRAB TAXI",
            "amount": -12.50,
            "bank": "DBS",
            "category": "Transport",
            "saved_at": "2024-01-20",
        }
    ]

    with patch("webapp.repository.get_db", return_value=mock_db):
        result = get_transactions_by_date_range("2024-01-01", "2024-01-31")

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]["category"] == "Transport"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_repository.py -v
```
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement `webapp/repository.py`**

```python
from datetime import datetime, timezone

import pandas as pd
from pymongo import ASCENDING

from webapp.db import get_db

_COLLECTION = "transactions"
_UPSERT_KEYS = ["date", "description", "amount", "bank"]


def save_transactions(df: pd.DataFrame) -> int:
    db = get_db()
    collection = db[_COLLECTION]

    # Ensure index exists for date-range queries
    collection.create_index([("date", ASCENDING)], background=True)

    saved_count = 0
    for _, row in df.iterrows():
        date_str = str(row["date"])
        filter_doc = {
            "date": date_str,
            "description": str(row["description"]),
            "amount": float(row["amount"]),
            "bank": str(row["bank"]),
        }
        update_doc = {
            "$set": {
                **filter_doc,
                "category": str(row.get("category", "Other")),
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        }
        collection.update_one(filter_doc, update_doc, upsert=True)
        saved_count += 1

    return saved_count


def get_transactions_by_date_range(start_date: str, end_date: str) -> pd.DataFrame:
    db = get_db()
    collection = db[_COLLECTION]

    cursor = collection.find(
        {"date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0},
        sort=[("date", ASCENDING)],
    )
    records = list(cursor)
    if not records:
        return pd.DataFrame(columns=["date", "description", "amount", "bank", "category", "saved_at"])

    return pd.DataFrame(records)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_repository.py -v
```
Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add webapp/repository.py tests/test_repository.py
git commit -m "feat: add MongoDB transaction repository with upsert and date-range query"
```

---

### Phase 6: UI — "Save to MongoDB" Button

#### Task 6: Add save flow to `webapp/helpers.py` and `webapp/app.py`

**Files:**
- Modify: `webapp/helpers.py` — add `categorize_and_save_df()`
- Modify: `webapp/app.py` — add button below CSV download

**Step 1: Write the failing test**

Add to `tests/test_helpers.py` (create if not exists):
```python
from unittest.mock import MagicMock, patch

import pandas as pd

from webapp.helpers import categorize_and_save_df


def make_df():
    return pd.DataFrame([
        {"date": "2024-01-15", "description": "GRAB TAXI", "amount": -12.50, "bank": "DBS"},
    ])


def test_categorize_and_save_df_returns_saved_count():
    df = make_df()
    with patch("webapp.helpers.categorize_transactions", return_value=df.assign(category=["Transport"])) as mock_cat, \
         patch("webapp.helpers.save_transactions", return_value=1) as mock_save:
        count = categorize_and_save_df(df)

    mock_cat.assert_called_once()
    mock_save.assert_called_once()
    assert count == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_helpers.py -v
```
Expected: FAIL with `ImportError: cannot import name 'categorize_and_save_df'`

**Step 3: Add `categorize_and_save_df` to `webapp/helpers.py`**

At the top of `webapp/helpers.py`, add imports:
```python
from webapp.categorizer import categorize_transactions
from webapp.repository import save_transactions
```

At the bottom of `webapp/helpers.py`, add the function:
```python
def categorize_and_save_df(df: pd.DataFrame) -> int:
    categorized = categorize_transactions(df)
    return save_transactions(categorized)
```

**Step 4: Add "Save to MongoDB" button in `webapp/app.py`**

In `webapp/app.py`, modify the `app()` function's `if df is not None:` block to call the new helper:

```python
if df is not None:
    show_df(df)
    _show_save_button(df)
```

Add `_show_save_button` function at the bottom of `webapp/app.py`:
```python
def _show_save_button(df: pd.DataFrame) -> None:
    from webapp.helpers import categorize_and_save_df  # avoid circular at module level

    if st.button("💾 Categorise & Save to MongoDB", type="primary"):
        try:
            with st.spinner("Categorising with AI and saving to MongoDB…"):
                count = categorize_and_save_df(df)
            st.success(f"✅ {count} transaction(s) saved to MongoDB.")
        except ValueError as e:
            st.error(f"Configuration error: {e}")
        except Exception as e:  # pylint: disable=broad-except
            st.error(f"Failed to save: {e}")
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_helpers.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add webapp/helpers.py webapp/app.py tests/test_helpers.py
git commit -m "feat: add 'Categorise & Save to MongoDB' button to main app"
```

---

### Phase 7: History Page

#### Task 7: Create `webapp/pages/3_history.py`

**Files:**
- Create: `webapp/pages/3_history.py`

**Step 1: Implement the history page**

```python
from datetime import date, timedelta

import streamlit as st

from webapp.repository import get_transactions_by_date_range


def history_page() -> None:
    st.set_page_config(page_title="Transaction History", layout="wide")
    st.title("📋 Transaction History")
    st.markdown("Browse transactions saved to MongoDB, filtered by date range.")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=date.today())

    if start_date > end_date:
        st.error("'From' date must be before 'To' date.")
        return

    if st.button("🔍 Load Transactions"):
        try:
            df = get_transactions_by_date_range(str(start_date), str(end_date))
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            return
        except Exception as e:  # pylint: disable=broad-except
            st.error(f"Failed to fetch data: {e}")
            return

        if df.empty:
            st.info("No transactions found for the selected date range.")
            return

        st.write(f"**{len(df)}** transaction(s) found.")

        # Category filter
        categories = ["All"] + sorted(df["category"].unique().tolist())
        selected_cat = st.selectbox("Filter by category", options=categories)
        if selected_cat != "All":
            df = df[df["category"] == selected_cat]

        desired_order = ["date", "description", "amount", "bank", "category", "saved_at"]
        df = df[[c for c in desired_order if c in df.columns]]
        df.columns = [c.replace("_", " ").title() for c in df.columns]

        st.dataframe(
            df.style.format({"Amount": "{:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", data=csv, mime="text/csv")


if __name__ == "__main__":
    history_page()
```

**Step 2: Commit**

```bash
git add webapp/pages/3_history.py
git commit -m "feat: add Transaction History Streamlit page (3_history.py)"
```

---

### Phase 8: Environment Variables Documentation

#### Task 8: Update README / document env vars

**Files:**
- Modify: `README.md` (find the environment variables or configuration section and add):

```markdown
### MongoDB + AI Categorisation

Set the following environment variables to enable AI categorisation and MongoDB storage:

| Variable         | Required | Description                                              |
|------------------|----------|----------------------------------------------------------|
| `DEEPSEEK_API_KEY` | Yes    | DeepSeek API key (get one at https://platform.deepseek.com) |
| `MONGODB_URL`    | Yes      | MongoDB Atlas connection string (e.g. `mongodb+srv://...`) |
| `MONGODB_DB_NAME`| No       | Database name (default: `bankclaw`)                      |
```

**Step 1: Commit**

```bash
git add README.md
git commit -m "docs: document DEEPSEEK_API_KEY and MONGODB_URL environment variables"
```

---

### Phase 9: Full Test Run

#### Task 9: Verify all tests pass

**Step 1: Run full test suite**

```bash
pytest tests/ -v
```
Expected: All existing tests pass plus all new tests pass.

**Step 2: If any failures, fix them before proceeding.**

---

## Testing Strategy

| Layer | File | What's tested |
|-------|------|---------------|
| Unit | `tests/test_db.py` | MongoDB connection, missing env var error |
| Unit | `tests/test_models.py` | `CategorizedTransaction` dataclass |
| Unit | `tests/test_categorizer.py` | DeepSeek API call, category validation, fallback to "Other" |
| Unit | `tests/test_repository.py` | Upsert logic, date-range query, DataFrame return |
| Unit | `tests/test_helpers.py` | `categorize_and_save_df` orchestration |
| Existing | `tests/test_app.py` | Full app flow (must still pass — no regression) |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DeepSeek returns malformed output (wrong number of lines) | `categorizer.py` pads/truncates to match DataFrame length; unknown values fall back to "Other" |
| MongoDB connection flaky in CI | Mock `pymongo` in all unit tests; only test real connection in manual integration test |
| Duplicate records on re-upload | Upsert by `{ date, description, amount, bank }` compound key |
| Rate limiting from DeepSeek on large statements | Single batch request for all transactions minimises API calls |
| `show_df` in `helpers.py` uses Streamlit — hard to unit test | `categorize_and_save_df` is a pure orchestration function that is easy to mock-test |

---

## Success Criteria

- [ ] `pytest tests/ -v` passes all tests (new + existing)
- [ ] `uv run streamlit run webapp/app.py` starts without errors when env vars are unset (errors shown inline, no crash)
- [ ] With `DEEPSEEK_API_KEY` and `MONGODB_URL` set, clicking "Categorise & Save to MongoDB" saves all records to Atlas
- [ ] "3 History" page loads and filters records by date range
- [ ] No duplicate records when the same PDF is uploaded and saved twice
- [ ] `ruff check webapp/` passes with no errors
