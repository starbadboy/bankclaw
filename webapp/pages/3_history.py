from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from webapp.auth import clear_auth_query_token, require_authentication
from webapp.repository import get_transactions_by_date_range

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

_HISTORY_UI_CSS = """
<style>
.history-shell {
    background: linear-gradient(145deg, #f8fafc 0%, #eef2ff 100%);
    border: 1px solid #dbeafe;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
}
.history-shell h2 {
    margin: 0;
    font-size: 1.35rem;
    color: #0f172a;
}
.history-shell p {
    margin: 6px 0 0 0;
    color: #475569;
}
.history-filter-shell {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #ffffff;
    padding: 14px 16px 10px 16px;
    margin-bottom: 14px;
}
</style>
"""


def history_page() -> None:
    current_user_email = require_authentication()
    st.set_page_config(page_title="Transaction History", layout="wide")
    _render_account_top_right(current_user_email)
    st.markdown(_HISTORY_UI_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="history-shell">
            <h2>Transaction History Workspace</h2>
            <p>Browse, filter, and export your saved transactions with a cleaner review flow.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="history-filter-shell">', unsafe_allow_html=True)
    st.markdown("### Transaction History")
    st.caption("Filter by date range to inspect and export your transaction records.")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=date.today())
    st.markdown("</div>", unsafe_allow_html=True)

    if start_date > end_date:
        st.error("'From' date must be before 'To' date.")
        return

    if st.button("🔍 Load Transactions"):
        try:
            df = get_transactions_by_date_range(
                str(start_date),
                str(end_date),
                user_email=current_user_email,
            )
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            return
        except Exception as e:  # pylint: disable=broad-except
            st.error(f"Failed to fetch data: {e}")
            return

        if df.empty:
            st.info("No transactions found for the selected date range.")
            return

        st.markdown(f"### Results ({len(df)} transactions)")

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
