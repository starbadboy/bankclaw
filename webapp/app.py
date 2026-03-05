from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from monopoly.pdf import MissingPasswordError, PdfDocument
from streamlit.runtime.uploaded_file_manager import UploadedFile

from webapp.categorizer import VALID_CATEGORIES, categorize_transactions
from webapp.constants import APP_DESCRIPTION
from webapp.helpers import create_df, parse_bank_statement, show_df
from webapp.logo import logo
from webapp.models import ProcessedFile
from webapp.repository import save_transactions

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# number of files that need to be added before progress bar appears
PBAR_MIN_FILES = 4


def app() -> pd.DataFrame:
    st.set_page_config(page_title="Statement Sensei", layout="wide")
    st.image(logo, width=450)
    st.markdown(APP_DESCRIPTION)

    files = get_files()

    df = None
    if "df" in st.session_state:
        df = st.session_state["df"]

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
    return st.file_uploader(
        label="Upload a bank statement",
        type="pdf",
        label_visibility="hidden",
        accept_multiple_files=True,
    )


def _show_categorise_button(df: pd.DataFrame) -> None:
    if st.button("🤖 Categorise with AI", type="primary"):
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
    st.subheader("Review & Edit Categories")
    st.caption("Change any category using the dropdown, then click Save.")

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
        if st.button("💾 Save to MongoDB", type="primary"):
            try:
                with st.spinner("Saving to MongoDB…"):
                    count = save_transactions(edited_df)
                st.success(f"✅ {count} transaction(s) saved to MongoDB.")
                del st.session_state["categorized_df"]
            except ValueError as e:
                st.error(f"Configuration error: {e}")
            except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
                st.error(f"Failed to save: {e}")

    with col2:
        if st.button("🔄 Reset & Re-categorise"):
            del st.session_state["categorized_df"]
            st.rerun()


if __name__ == "__main__":
    app()
