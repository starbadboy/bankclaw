from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from monopoly.pdf import MissingPasswordError, PdfDocument
from streamlit.errors import NoSessionContext
from streamlit.runtime.uploaded_file_manager import UploadedFile

from webapp.auth import (
    clear_auth_query_token,
    create_auth_token,
    get_current_user_email,
    hash_password,
    init_auth_state,
    is_authenticated,
    normalize_email,
    restore_auth_from_query_token,
    verify_password,
)
from webapp.categorizer import VALID_CATEGORIES, categorize_transactions
from webapp.constants import APP_DESCRIPTION
from webapp.helpers import create_df, parse_bank_statement, show_df
from webapp.logo import logo
from webapp.models import ProcessedFile
from webapp.repository import save_transactions
from webapp.user_repository import authenticate_user, create_user

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# number of files that need to be added before progress bar appears
PBAR_MIN_FILES = 4

_MODERN_UI_CSS = """
<style>
.ss-hero {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 18px 20px;
    margin: 8px 0 18px 0;
}
.ss-hero h2 {
    margin: 0;
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f172a;
}
.ss-hero p {
    margin: 8px 0 0 0;
    color: #475569;
}
.workflow {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}
.workflow-step {
    border: 1px solid #dbe3f0;
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 0.85rem;
    color: #334155;
    background: #f8fafc;
}
.workflow-step.current {
    background: #eef2ff;
    border-color: #c7d2fe;
    color: #1e3a8a;
    font-weight: 600;
}
</style>
"""


def app() -> pd.DataFrame:
    st.set_page_config(page_title="Statement Sensei", layout="wide")
    st.image(logo, width=450)
    _inject_modern_css()
    _render_hero()
    init_auth_state(st.session_state)
    restore_auth_from_query_token(st.session_state, st.query_params)

    if not is_authenticated(st.session_state):
        _show_auth_screen()
        return None

    if _redirect_to_visualizations():
        return None

    _show_logged_in_banner()

    files = get_files()

    df = None
    if "df" in st.session_state:
        df = st.session_state["df"]
    _render_workflow(has_df=df is not None, has_categorized=st.session_state.get("categorized_df") is not None)

    if files:
        processed_files = process_files(files)

        if processed_files:
            df = create_df(processed_files)

    if df is not None:
        show_df(df)
        categorized_df = st.session_state.get("categorized_df")
        if categorized_df is None:
            _show_categorise_button(df)
        else:
            _show_review_and_save(categorized_df)

    return df


def _inject_modern_css() -> None:
    st.markdown(_MODERN_UI_CSS, unsafe_allow_html=True)


def _render_hero() -> None:
    st.markdown(
        """
        <div class="ss-hero">
            <h2>Convert statements with confidence</h2>
            <p>Upload statement PDFs, review AI categories, and save clean records for long-term insights.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(APP_DESCRIPTION)


def _render_workflow(*, has_df: bool, has_categorized: bool) -> None:
    current_step = "Upload PDFs"
    if has_df:
        current_step = "Review Categories" if has_categorized else "Categorise with AI"

    steps = ["Upload PDFs", "Categorise with AI", "Review Categories", "Save to MongoDB", "Explore Insights"]
    rendered_steps = []
    for step in steps:
        css_class = "workflow-step current" if step == current_step else "workflow-step"
        suffix = " (Current)" if step == current_step else ""
        rendered_steps.append(f'<span class="{css_class}">{step}{suffix}</span>')

    st.markdown(f'<div class="workflow">{"".join(rendered_steps)}</div>', unsafe_allow_html=True)


def _show_logged_in_banner() -> None:
    user_email = get_current_user_email(st.session_state)
    col1, col2 = st.columns([5, 1])
    col1.caption(f"Signed in as `{user_email}`")
    if col2.button("Logout"):
        _clear_persistent_auth()
        st.session_state["auth_user"] = None
        st.rerun()


def _redirect_to_visualizations() -> bool:
    try:
        st.switch_page("pages/1_visualizations.py")
        return True
    except NoSessionContext:
        return False


def _show_auth_screen() -> None:
    st.subheader("Welcome back")
    st.caption("Sign in to continue, or create an account to keep your own saved transaction history.")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Sign in", type="primary", key="login_button"):
            email = normalize_email(login_email)
            user = authenticate_user(email)
            if not user or not verify_password(login_password, user["password_hash"]):
                st.error("Invalid email or password.")
            else:
                st.session_state["auth_user"] = {"email": user["email"]}
                _set_persistent_auth(user["email"])
                st.success("Login successful.")
                if not _redirect_to_visualizations():
                    st.rerun()

    with tab_register:
        register_email = st.text_input("Email", key="register_email")
        register_password = st.text_input("Password", type="password", key="register_password")
        if st.button("Create account", key="register_button"):
            email = normalize_email(register_email)
            if "@" not in email:
                st.error("Please enter a valid email.")
                return
            if len(register_password) < 8:
                st.error("Password must be at least 8 characters.")
                return

            created = create_user(email, hash_password(register_password))
            if not created:
                st.warning("Account already exists. Please log in instead.")
            else:
                st.success("Registration successful. Please log in.")


def _set_persistent_auth(email: str) -> None:
    st.query_params["auth"] = create_auth_token(email)


def _clear_persistent_auth() -> None:
    clear_auth_query_token(st.query_params)


def process_files(uploaded_files: list[UploadedFile]) -> list[ProcessedFile] | None:
    num_files = len(uploaded_files)
    show_pbar = num_files > PBAR_MIN_FILES

    pbar = st.progress(0, text="Processing PDFs") if show_pbar else None

    processed_files = []
    for i, file in enumerate(uploaded_files):
        if pbar:
            pbar.progress(i / num_files, text=f"Processing {file.name}")

        file_bytes = file.getvalue()
        document = PdfDocument(file_bytes=file_bytes)
        document._name = file.name

        # attempt to use passwords stored in environment to unlock
        # if no passwords in environment, then ask user for password
        if document.is_encrypted:  # pylint: disable=no-member
            try:
                document = document.unlock_document()

            except MissingPasswordError:
                document = handle_encrypted_document(document)

        if document:
            processed_file = handle_file(document)
            processed_files.append(processed_file)

    if pbar:
        pbar.empty()

    return processed_files


def handle_file(document: PdfDocument) -> ProcessedFile | None:
    document_id = document.xref_get_key(-1, "ID")[-1]
    uuid = document.name + document_id
    if uuid in st.session_state:
        return st.session_state[uuid]

    file = parse_bank_statement(document)
    st.session_state[uuid] = file
    return file


def handle_encrypted_document(document: PdfDocument) -> PdfDocument | None:
    passwords: list[str] = st.session_state.setdefault("pdf_passwords", [])

    # Try existing passwords first
    for password in passwords:
        document.authenticate(password)
        if not document.is_encrypted:  # pylint: disable=no-member
            return document

    # Prompt user for password if none of the existing passwords work
    password_container = st.empty()
    password = password_container.text_input(
        label="Password",
        type="password",
        placeholder=f"Enter password for {document.name}",
        key=document.name,
    )

    if not password:
        return None

    document.authenticate(password)

    if not document.is_encrypted:  # pylint: disable=no-member
        passwords.append(password)
        password_container.empty()
        return document

    st.error("Wrong password. Please try again.")
    return None


def get_files() -> list[UploadedFile]:
    st.caption("Step 1: Upload one or more PDF statements to begin.")
    return st.file_uploader(
        label="Upload a bank statement",
        type="pdf",
        label_visibility="hidden",
        accept_multiple_files=True,
    )


def _show_categorise_button(df: pd.DataFrame) -> None:
    st.caption("Step 2: Let AI suggest categories for each transaction before you review.")
    if st.button("🤖 Generate AI Categories", type="primary"):
        try:
            with st.spinner("Asking DeepSeek to categorise your transactions…"):
                categorized = categorize_transactions(df)
            st.session_state["categorized_df"] = categorized
            st.rerun()
        except ValueError as e:
            st.error(f"Configuration error: {e}")
        except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
            st.error(f"Categorisation failed: {e}")


def _show_review_and_save(categorized_df: pd.DataFrame) -> None:
    st.subheader("Step 3: Review & Edit Categories")
    st.caption("Adjust any category with the dropdown, then save when everything looks right.")

    edited_df = st.data_editor(
        categorized_df,
        column_config={
            "category": st.column_config.SelectboxColumn(
                label="Category",
                options=VALID_CATEGORIES,
                required=True,
            ),
            "date": st.column_config.TextColumn("Date", disabled=True),
            "description": st.column_config.TextColumn("Description", disabled=True),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f", disabled=True),
            "bank": st.column_config.TextColumn("Bank", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="category_editor",
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("💾 Save Reviewed Transactions", type="primary"):
            try:
                with st.spinner("Saving to MongoDB…"):
                    user_email = get_current_user_email(st.session_state)
                    if not user_email:
                        st.error("Please log in before saving.")
                        return
                    count = save_transactions(edited_df, user_email=user_email)
                st.success(f"✅ {count} transaction(s) saved to MongoDB.")
                st.session_state.pop("categorized_df", None)
            except ValueError as e:
                st.error(f"Configuration error: {e}")
            except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
                st.error(f"Failed to save: {e}")

    with col2:
        if st.button("🔄 Re-run AI Categorisation"):
            st.session_state.pop("categorized_df", None)
            st.rerun()


if __name__ == "__main__":
    app()
