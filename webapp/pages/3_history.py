from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from webapp.auth import clear_auth_query_token, require_authentication
from webapp.categorizer import VALID_CATEGORIES
from webapp.repository import delete_transactions, get_transactions_by_date_range, save_category_memory, save_transactions

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")
_DELETE_COL = "_delete"
_DELETE_MARKS_KEY = "history_delete_marks"

def _build_row_mask(df, row):  # noqa: ANN001
    return (
        (df["date"] == row["date"])
        & (df["description"] == row["description"])
        & (df["amount"] == row["amount"])
        & (df["bank"] == row["bank"])
    )


def _build_row_key(row) -> str:  # noqa: ANN001
    return f"{row['date']}|{row['description']}|{row['amount']}|{row['bank']}"


def _apply_delete_marks(df):  # noqa: ANN001
    marks = st.session_state.get(_DELETE_MARKS_KEY, {})
    df[_DELETE_COL] = df.apply(lambda row: bool(marks.get(_build_row_key(row), False)), axis=1)
    return df


def _update_delete_marks_from_editor(edited_df) -> None:  # noqa: ANN001
    marks = st.session_state.get(_DELETE_MARKS_KEY, {})
    for _, row in edited_df.iterrows():
        row_key = _build_row_key(row)
        if bool(row.get(_DELETE_COL, False)):
            marks[row_key] = True
        else:
            marks.pop(row_key, None)
    st.session_state[_DELETE_MARKS_KEY] = marks


def _sync_category_changes(original_df, edited_df, user_email: str) -> tuple[int, str | None]:  # noqa: ANN001
    changed_rows = edited_df.loc[edited_df["category"] != original_df["category"]].copy()
    if _DELETE_COL in changed_rows.columns:
        changed_rows = changed_rows.loc[changed_rows[_DELETE_COL] != True].copy()  # noqa: E712
    if changed_rows.empty:
        return 0, None

    save_payload = changed_rows[["date", "description", "amount", "bank", "category"]].copy()
    updated_count = save_transactions(save_payload, user_email=user_email)
    memory_payload = changed_rows[["description", "category"]].copy()
    memory_warning = None
    try:
        save_category_memory(memory_payload, user_email=user_email, source="manual")
    except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
        memory_warning = f"Category updates were saved, but category memory could not be updated: {e}"
    base_df = st.session_state["history_df"].copy()
    for _, row in save_payload.iterrows():
        base_df.loc[_build_row_mask(base_df, row), "category"] = row["category"]
    st.session_state["history_df"] = base_df
    return updated_count, memory_warning


def _sync_deleted_rows(edited_df, user_email: str) -> int:  # noqa: ANN001
    if _DELETE_COL not in edited_df.columns:
        return 0

    selected_for_delete = edited_df.loc[edited_df[_DELETE_COL] == True].copy()  # noqa: E712
    if selected_for_delete.empty:
        return 0

    delete_payload = selected_for_delete[["date", "description", "amount", "bank"]].copy()
    deleted_count = delete_transactions(delete_payload, user_email=user_email)

    base_df = st.session_state["history_df"].copy()
    for _, row in delete_payload.iterrows():
        base_df = base_df.loc[~_build_row_mask(base_df, row)].copy()
    st.session_state["history_df"] = base_df
    marks = st.session_state.get(_DELETE_MARKS_KEY, {})
    for _, row in delete_payload.iterrows():
        marks.pop(_build_row_key(row), None)
    st.session_state[_DELETE_MARKS_KEY] = marks
    return deleted_count


def _pending_delete_payload(edited_df):  # noqa: ANN001
    if _DELETE_COL not in edited_df.columns:
        return edited_df.iloc[0:0][["date", "description", "amount", "bank"]]
    selected_for_delete = edited_df.loc[edited_df[_DELETE_COL] == True].copy()  # noqa: E712
    if selected_for_delete.empty:
        return edited_df.iloc[0:0][["date", "description", "amount", "bank"]]
    return selected_for_delete[["date", "description", "amount", "bank"]].copy()


def _clear_delete_marks(delete_payload) -> None:  # noqa: ANN001
    marks = st.session_state.get(_DELETE_MARKS_KEY, {})
    for _, row in delete_payload.iterrows():
        marks.pop(_build_row_key(row), None)
    st.session_state[_DELETE_MARKS_KEY] = marks


def _fetch_history(start_date: date, end_date: date, user_email: str) -> bool:
    if not st.button("🔍 Load Transactions"):
        return True
    try:
        st.session_state["history_df"] = get_transactions_by_date_range(
            str(start_date),
            str(end_date),
            user_email=user_email,
        )
        return True
    except ValueError as e:
        st.error(f"Configuration error: {e}")
    except Exception as e:  # pylint: disable=broad-except
        st.error(f"Failed to fetch data: {e}")
    return False


def history_page() -> None:
    current_user_email = require_authentication()
    st.set_page_config(page_title="Transaction History", layout="wide")
    _render_account_top_right(current_user_email)
    st.markdown("### Transaction History")
    st.caption("Filter by date range to inspect and export your transaction records.")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=date.today())

    if start_date > end_date:
        st.error("'From' date must be before 'To' date.")
        return
    if not _fetch_history(start_date, end_date, current_user_email):
        return

    df = st.session_state.get("history_df")
    if df is None:
        return
    if df.empty:
        st.info("No transactions found for the selected date range.")
        return

    st.markdown(f"### Results ({len(df)} transactions)")
    categories = ["All"] + sorted(df["category"].unique().tolist())
    selected_cat = st.selectbox("Filter by category", options=categories)
    df = df[df["category"] == selected_cat].copy() if selected_cat != "All" else df.copy()

    desired_order = ["date", "description", "amount", "bank", "category", "saved_at"]
    df = df[[c for c in desired_order if c in df.columns]]
    df = _apply_delete_marks(df)
    original_df = df.copy()
    edited_df = st.data_editor(
        df,
        column_config={
            _DELETE_COL: st.column_config.CheckboxColumn("🗑️"),
            "category": st.column_config.SelectboxColumn("Category", options=VALID_CATEGORIES, required=True),
            "date": st.column_config.TextColumn("Date", disabled=True),
            "description": st.column_config.TextColumn("Description", disabled=True),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f", disabled=True),
            "bank": st.column_config.TextColumn("Bank", disabled=True),
            "saved_at": st.column_config.TextColumn("Saved At", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="history_editor",
    )
    if _DELETE_COL not in edited_df.columns:
        edited_df[_DELETE_COL] = False
    _update_delete_marks_from_editor(edited_df)

    updated_count, memory_warning = _sync_category_changes(original_df, edited_df, current_user_email)
    if updated_count:
        if memory_warning:
            st.warning(memory_warning)
        st.success(f"Saved category updates for {updated_count} transaction(s).")
        st.session_state.pop("history_editor", None)
        st.rerun()

    delete_payload = _pending_delete_payload(edited_df)
    if not delete_payload.empty:
        st.warning(f"Are you sure you want to delete {len(delete_payload)} transaction(s)?")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Confirm Delete", type="primary"):
                deleted_count = _sync_deleted_rows(edited_df, current_user_email)
                st.success(f"Deleted {deleted_count} transaction(s).")
                st.session_state.pop("history_editor", None)
                st.rerun()
        with cancel_col:
            if st.button("Cancel"):
                cancel_df = edited_df.copy()
                if _DELETE_COL in cancel_df.columns:
                    cancel_df[_DELETE_COL] = False
                updated_count, memory_warning = _sync_category_changes(original_df, cancel_df, current_user_email)
                if memory_warning:
                    st.warning(memory_warning)
                if updated_count:
                    st.success(f"Saved category updates for {updated_count} transaction(s).")
                _clear_delete_marks(delete_payload)
                st.session_state.pop("history_editor", None)
                st.rerun()

    csv = edited_df.drop(columns=[_DELETE_COL], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, mime="text/csv")


def _render_account_top_right(user_email: str) -> None:
    _, right_col = st.columns([6, 1])
    with right_col:
        st.caption(f"`{user_email}`")
        if st.button("Logout", key="history_logout"):
            st.session_state["auth_user"] = None
            clear_auth_query_token(st.query_params)
            st.switch_page("app.py")


if __name__ == "__main__":
    history_page()
