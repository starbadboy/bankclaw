from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from webapp.auth import clear_auth_query_token, require_authentication
from webapp.category_definitions import get_effective_categories, validate_custom_category_name
from webapp.repository import (
    archive_custom_category,
    delete_transactions,
    get_custom_categories,
    get_transactions_by_date_range,
    save_category_memory,
    save_custom_category,
    save_transactions,
)

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")
_DELETE_COL = "_delete"
_DELETE_MARKS_KEY = "history_delete_marks"
_DOWNLOAD_LABEL = "Download CSV"
_CSV_MIME_TYPE = "text/csv"
_HISTORY_CSS = """
<style>
div[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top right, rgba(47, 107, 255, 0.16), transparent 28%),
        radial-gradient(circle at top left, rgba(0, 214, 201, 0.08), transparent 26%),
        linear-gradient(180deg, #071120 0%, #0a1628 52%, #0d1b30 100%);
}
.history-shell {
    border: 1px solid rgba(129, 177, 255, 0.16);
    border-radius: 24px;
    padding: 22px 24px;
    margin-bottom: 16px;
    background: linear-gradient(145deg, rgba(8, 18, 36, 0.96), rgba(13, 27, 48, 0.92));
    box-shadow: 0 24px 64px rgba(2, 6, 23, 0.42);
}
.history-shell strong {
    display: block;
    margin-bottom: 6px;
    color: #7dd3fc;
    font-size: 0.76rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
.history-shell h2 {
    margin: 0 0 6px 0;
    color: #f8fbff;
    font-size: 1.7rem;
}
.history-shell p {
    margin: 0;
    color: #bcd2f7;
}
.history-filter-shell,
.history-results-shell {
    border: 1px solid rgba(129, 177, 255, 0.14);
    border-radius: 18px;
    padding: 14px 16px 12px 16px;
    background: linear-gradient(180deg, rgba(13, 25, 46, 0.92), rgba(9, 18, 34, 0.90));
    margin-bottom: 14px;
}
</style>
"""

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


def _category_key(category: str) -> str:
    return " ".join(str(category).split()).casefold()


def _find_legacy_categories(df, active_categories: list[str]) -> list[str]:  # noqa: ANN001
    active_keys = {_category_key(category) for category in active_categories}
    legacy_categories: list[str] = []

    for raw_category in df["category"].dropna().tolist():
        cleaned_category = " ".join(str(raw_category).split())
        if not cleaned_category or _category_key(cleaned_category) in active_keys:
            continue
        if cleaned_category in legacy_categories:
            continue
        legacy_categories.append(cleaned_category)

    return legacy_categories


def _is_legacy_category(category: str, active_categories: list[str]) -> bool:
    active_keys = {_category_key(active_category) for active_category in active_categories}
    return _category_key(category) not in active_keys


def _load_category_options(user_email: str) -> list[str] | None:
    try:
        return get_effective_categories(user_email)
    except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
        st.error(f"Failed to load category options: {e}")
        return None


def _render_legacy_history_rows(legacy_df, legacy_categories: list[str]) -> None:  # noqa: ANN001
    if not legacy_categories:
        return

    joined_categories = ", ".join(sorted(legacy_categories))
    st.warning(
        "Some saved transactions use categories that are no longer active: "
        f"{joined_categories}. You can keep viewing those records, but new selections use only active categories."
    )
    st.dataframe(legacy_df, use_container_width=True, hide_index=True)


def _download_history_csv(edited_df, legacy_df) -> None:  # noqa: ANN001
    download_df = pd.concat(
        [
            edited_df.drop(columns=[_DELETE_COL], errors="ignore"),
            legacy_df,
        ],
        ignore_index=True,
    )
    csv = download_df.to_csv(index=False).encode("utf-8")
    st.download_button(_DOWNLOAD_LABEL, data=csv, mime=_CSV_MIME_TYPE)


def _render_read_only_history_rows(df) -> None:  # noqa: ANN001
    st.warning("Category options are temporarily unavailable, so history is in read-only mode for now.")
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(_DOWNLOAD_LABEL, data=csv, mime=_CSV_MIME_TYPE)


def _handle_delete_confirmation(edited_df, original_df, current_user_email: str) -> None:  # noqa: ANN001
    delete_payload = _pending_delete_payload(edited_df)
    if delete_payload.empty:
        return

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


def _render_editable_history_rows(editable_df, legacy_df, current_user_email: str, category_options: list[str]) -> None:  # noqa: ANN001
    if editable_df.empty:
        csv = pd.concat([editable_df, legacy_df], ignore_index=True).to_csv(index=False).encode("utf-8")
        st.download_button(_DOWNLOAD_LABEL, data=csv, mime=_CSV_MIME_TYPE)
        return

    editable_df = _apply_delete_marks(editable_df)
    original_df = editable_df.copy()
    edited_df = st.data_editor(
        editable_df,
        column_config={
            _DELETE_COL: st.column_config.CheckboxColumn("🗑️"),
            "category": st.column_config.SelectboxColumn("Category", options=category_options, required=True),
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

    _handle_delete_confirmation(edited_df, original_df, current_user_email)
    _download_history_csv(edited_df, legacy_df)


def _render_history_results(df, current_user_email: str) -> None:  # noqa: ANN001
    st.markdown(f'<div class="history-results-shell"><strong>Results</strong><p>{len(df)} transactions</p></div>', unsafe_allow_html=True)
    categories = ["All"] + sorted(df["category"].unique().tolist())
    selected_cat = st.selectbox("Filter by category", options=categories)
    df = df[df["category"] == selected_cat].copy() if selected_cat != "All" else df.copy()

    desired_order = ["date", "description", "amount", "bank", "category", "saved_at"]
    df = df[[c for c in desired_order if c in df.columns]]
    category_options = _load_category_options(current_user_email)
    if category_options is None:
        _render_read_only_history_rows(df)
        return
    legacy_mask = df["category"].apply(lambda category: _is_legacy_category(str(category), category_options))
    legacy_df = df.loc[legacy_mask].copy()
    editable_df = df.loc[~legacy_mask].copy()
    legacy_categories = _find_legacy_categories(df, category_options)

    _render_legacy_history_rows(legacy_df, legacy_categories)
    _render_editable_history_rows(editable_df, legacy_df, current_user_email, category_options)


def _render_category_manager(user_email: str) -> None:
    custom_cats_df = get_custom_categories(user_email)
    custom_names = custom_cats_df["name"].tolist() if not custom_cats_df.empty else []

    with st.expander("⚙️ Manage Categories", expanded=False):
        _render_add_category_form(user_email, custom_names)
        _render_custom_categories_list(user_email, custom_names)


def _render_add_category_form(user_email: str, custom_names: list[str]) -> None:
    from webapp.category_definitions import DEFAULT_CATEGORIES  # noqa: PLC0415

    st.caption("Add a custom category to use alongside the built-in defaults.")
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        new_name = st.text_input("New category name", label_visibility="collapsed", placeholder="e.g. Pet Care")
    with col_btn:
        if st.button("Add Category", key="cat_mgr_add", use_container_width=True):
            existing = list(DEFAULT_CATEGORIES) + custom_names
            try:
                cleaned = validate_custom_category_name(new_name, existing)
            except ValueError as exc:
                st.error(str(exc))
                return
            save_custom_category(cleaned, user_email)
            st.success(f'Category "{cleaned}" added.')
            st.rerun()


def _render_custom_categories_list(user_email: str, custom_names: list[str]) -> None:
    from webapp.category_definitions import DEFAULT_CATEGORIES  # noqa: PLC0415

    st.caption("Active categories (built-in are read-only; your custom ones can be archived).")
    all_active = [c for c in DEFAULT_CATEGORIES if c != "Other"] + custom_names + ["Other"]

    for cat in all_active:
        row_col, btn_col = st.columns([5, 1])
        is_custom = cat in custom_names
        label = f"**{cat}**" if is_custom else cat
        with row_col:
            st.markdown(label)
        with btn_col:
            if is_custom and st.button("Archive", key=f"cat_mgr_archive_{cat}", use_container_width=True):
                archive_custom_category(cat, user_email)
                st.success(f'"{cat}" archived.')
                st.rerun()


def history_page() -> None:
    current_user_email = require_authentication()
    st.set_page_config(page_title="Transaction History", layout="wide")
    st.markdown(_HISTORY_CSS, unsafe_allow_html=True)
    _render_account_top_right(current_user_email)
    st.markdown(
        """
        <section class="history-shell">
            <strong>Transaction History Workspace</strong>
            <h2>Review and maintain saved transactions</h2>
            <p>Filter historical records, make category corrections, and export clean datasets from one dashboard surface.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    _render_category_manager(current_user_email)
    st.markdown(
        """
        <div class="history-filter-shell">
            <strong style="display:block; margin-bottom:6px; color:#7dd3fc; letter-spacing:0.18em; text-transform:uppercase; font-size:0.74rem;">Filter Range</strong>
            <p style="margin:0; color:#8da6d1;">Choose the time window you want to inspect before loading or exporting transactions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
    _render_history_results(df, current_user_email)


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
