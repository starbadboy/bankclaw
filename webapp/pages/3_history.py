from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from webapp.repository import get_transactions_by_date_range

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")


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
