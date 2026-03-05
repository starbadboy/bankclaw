from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from dotenv import load_dotenv

from webapp.auth import clear_auth_query_token, require_authentication
from webapp.categorizer import VALID_CATEGORIES, categorize_transactions
from webapp.constants import SUPPORTED_BANKS
from webapp.helpers import create_df
from webapp.visualizations_helpers import compute_category_expenses, compute_monthly_cash_flow
from webapp.repository import get_transactions_by_date_range, save_transactions
from webapp.app import process_files

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

current_user_email = require_authentication()


# ── MongoDB Historical Cash Flow Dashboard ──────────────────────────────────

_CATEGORY_COLORS = [
    "#00CEAA",
    "#F63366",
    "#3D9BE9",
    "#F5A623",
    "#7B68EE",
    "#50C878",
    "#FF6B6B",
    "#4ECDC4",
    "#FFE66D",
    "#A8A8A8",
]
_HOVERINFO_TEXT_NAME = "text+name"
_HTML_DIV_CLOSE = "</div>"

_KPI_CSS = """
<style>
.insights-shell {
    background: linear-gradient(145deg, #f8fafc 0%, #eef2ff 100%);
    border: 1px solid #dbeafe;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
}
.insights-filter-shell {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #ffffff;
    padding: 14px 16px 6px 16px;
    margin-bottom: 14px;
}
.insights-control-shell {
    border: 1px solid #dbe7ff;
    border-radius: 14px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    padding: 14px 16px 12px 16px;
    margin-bottom: 16px;
}
.insights-section-shell {
    border: 1px solid #e5e7eb;
    background: #ffffff;
    border-radius: 16px;
    padding: 14px 16px 8px 16px;
    margin-top: 14px;
}
.insights-section-shell h3 {
    margin: 0 0 4px 0;
    color: #0f172a;
    font-size: 1.05rem;
}
.insights-section-shell p {
    margin: 0;
    color: #64748b;
    font-size: 0.9rem;
}
.insights-chart-shell {
    border: 1px solid #edf0f5;
    border-radius: 14px;
    padding: 12px 12px 4px 12px;
    background: #fcfdff;
}
.kpi-card {
    background: rgba(0,0,0,0.03);
    border: 1px solid rgba(0,0,0,0.09);
    border-radius: 12px;
    padding: 18px 12px;
    text-align: center;
}
.kpi-label {
    font-size: 11px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.1;
}
.bank-info-thumb {
    border: 1px solid #dbeafe;
    background: #f8fbff;
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
</style>
"""


def _render_kpi(col, label: str, value: str, color: str = "#262730") -> None:
    col.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="color:{color};">{value}</div></div>',
        unsafe_allow_html=True,
    )


def _show_cash_flow_chart(monthly: pd.DataFrame) -> None:
    income_bar = go.Bar(
        x=monthly.index,
        y=monthly["Income"],
        name="Income",
        marker={"color": "#00CEAA", "cornerradius": 8},
        hovertext=[f"${v:,.0f}" for v in monthly["Income"]],
        hoverinfo=_HOVERINFO_TEXT_NAME,
    )
    expense_bar = go.Bar(
        x=monthly.index,
        y=[-v for v in monthly["Expenses"]],
        name="Expenses",
        marker={"color": "#F63366", "cornerradius": 8},
        hovertext=[f"${v:,.0f}" for v in monthly["Expenses"]],
        hoverinfo=_HOVERINFO_TEXT_NAME,
    )
    net_line = go.Scatter(
        x=monthly.index,
        y=monthly["Net"],
        name="Net",
        mode="lines+markers",
        line={"color": "#262730", "width": 3},
        hovertext=[f"${v:,.0f}" for v in monthly["Net"]],
        hoverinfo=_HOVERINFO_TEXT_NAME,
    )
    layout = go.Layout(
        title="Monthly Cash Flow",
        title_font={"size": 20},
        xaxis={"title": "Month", "showgrid": False, "dtick": "M1"},
        yaxis={
            "showgrid": True,
            "gridcolor": "#eef2f7",
            "zeroline": True,
            "zerolinecolor": "#EFEFEF",
            "zerolinewidth": 2,
            "tickformat": "$,.1s",
        },
        barmode="relative",
        hovermode="x unified",
        bargap=0.5,
        showlegend=True,
        legend={"orientation": "h", "y": 1.12, "x": 0.01},
        plot_bgcolor="#fcfdff",
        paper_bgcolor="#fcfdff",
    )
    st.plotly_chart(go.Figure(data=[income_bar, expense_bar, net_line], layout=layout), use_container_width=True)


def _show_pl_chart(monthly: pd.DataFrame) -> None:
    colors = ["#00CEAA" if v >= 0 else "#F63366" for v in monthly["Net"]]
    fig = go.Figure(
        data=[
            go.Bar(
                x=monthly.index,
                y=monthly["Net"],
                name="Net",
                marker={"color": colors, "cornerradius": 8},
                hovertext=[f"${v:,.0f}" for v in monthly["Net"]],
                hoverinfo=_HOVERINFO_TEXT_NAME,
            )
        ],
        layout=go.Layout(
            title="Monthly Profit / Loss",
            title_font={"size": 18},
            xaxis={"showgrid": False, "dtick": "M1"},
            yaxis={
                "showgrid": True,
                "gridcolor": "#eef2f7",
                "zeroline": True,
                "zerolinecolor": "#EFEFEF",
                "zerolinewidth": 2,
                "tickformat": "$,.1s",
            },
            bargap=0.5,
            plot_bgcolor="#fcfdff",
            paper_bgcolor="#fcfdff",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_category_donut(cat_expenses: pd.Series) -> None:
    fig = go.Figure(
        data=[
            go.Pie(
                labels=cat_expenses.index,
                values=cat_expenses.values,
                hole=0.55,
                marker={"colors": _CATEGORY_COLORS[: len(cat_expenses)]},
                textinfo="label+percent",
                hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
            )
        ],
        layout=go.Layout(
            title="Expenses by Category",
            title_font={"size": 18},
            showlegend=False,
            plot_bgcolor="#fcfdff",
            paper_bgcolor="#fcfdff",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_mongodb_dashboard(df: pd.DataFrame) -> None:
    st.markdown(_KPI_CSS, unsafe_allow_html=True)
    monthly = compute_monthly_cash_flow(df)
    cat_expenses = compute_category_expenses(df)

    total_income = round(monthly["Income"].sum())
    total_expenses = round(monthly["Expenses"].sum())
    total_net = round(monthly["Net"].sum())
    savings_rate = total_net / total_income * 100 if total_income > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    _render_kpi(c1, "Cash Going In", f"${total_income:,}", "#00CEAA")
    _render_kpi(c2, "Cash Going Out", f"${total_expenses:,}", "#F63366")
    net_str = f"-${abs(total_net):,}" if total_net < 0 else f"${total_net:,}"
    net_color = "#00CEAA" if total_net >= 0 else "#F63366"
    _render_kpi(c3, "Net Savings", net_str, net_color)
    _render_kpi(c4, "Savings Rate", f"{savings_rate:.1f}%", "#00CEAA" if savings_rate >= 0 else "#F63366")

    st.markdown(
        """
        <div class="insights-section-shell">
            <h3>Primary Trend</h3>
            <p>Track inflow, outflow, and monthly net movement in one view.</p>
        </div>
        <div class="insights-chart-shell">
        """,
        unsafe_allow_html=True,
    )
    _show_cash_flow_chart(monthly)
    st.markdown(_HTML_DIV_CLOSE, unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(
            """
            <div class="insights-section-shell">
                <h3>Profitability Snapshot</h3>
                <p>Compare monthly gains and losses to identify trend shifts.</p>
            </div>
            <div class="insights-chart-shell">
            """,
            unsafe_allow_html=True,
        )
        _show_pl_chart(monthly)
        st.markdown(_HTML_DIV_CLOSE, unsafe_allow_html=True)
    with col_right:
        if not cat_expenses.empty:
            st.markdown(
                """
                <div class="insights-section-shell">
                    <h3>Category Breakdown</h3>
                    <p>See where spending concentration is highest by category.</p>
                </div>
                <div class="insights-chart-shell">
                """,
                unsafe_allow_html=True,
            )
            _show_category_donut(cat_expenses)
            st.markdown(_HTML_DIV_CLOSE, unsafe_allow_html=True)


def _render_supported_banks_thumbnail() -> None:
    st.markdown(
        """
        <div class="bank-info-thumb">
            <strong>Supported Banks</strong><br/>
            Check whether your bank statement format is supported before processing.
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("View full supported bank list"):
        st.markdown(SUPPORTED_BANKS)


def _render_account_top_right(user_email: str) -> None:
    _, right_col = st.columns([6, 1])
    with right_col:
        st.caption(f"`{user_email}`")
        if st.button("Logout", key="viz_logout"):
            st.session_state["auth_user"] = None
            clear_auth_query_token(st.query_params)
            st.switch_page("app.py")


def _open_upload_dialog() -> None:
    st.session_state["viz_upload_dialog_open"] = True


def _maybe_open_upload_dialog(user_email: str) -> None:
    if st.session_state.get("viz_upload_dialog_open"):
        _show_upload_dialog(user_email)


@st.dialog("Upload statement PDFs")
def _show_upload_dialog(user_email: str) -> None:
    # Mark as handled for this render to avoid duplicate dialog creation.
    st.session_state["viz_upload_dialog_open"] = False
    _render_supported_banks_thumbnail()
    uploaded_files = st.file_uploader(
        "Upload one or more statement PDFs",
        type="pdf",
        accept_multiple_files=True,
        key="viz_upload_files",
    )
    review_df = st.session_state.get("viz_upload_review_df")

    if review_df is None:
        process_col, status_col = st.columns([2, 3])
        with process_col:
            process_clicked = st.button("Process with AI Categories", type="primary", key="viz_process_ai")
        with status_col:
            if not process_clicked:
                st.caption("AI analysis status will appear here.")
        if process_clicked:
            if not uploaded_files:
                st.warning("Please upload at least one PDF.")
                return
            processed_files = process_files(uploaded_files)
            if not processed_files:
                st.warning("No valid statements were processed.")
                return
            raw_df = create_df(processed_files)
            try:
                with status_col:
                    with st.spinner("Analyzing with AI..."):
                        categorized_df = categorize_transactions(raw_df)
            except ValueError as e:
                st.error(f"Configuration error: {e}")
                return
            except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
                st.error(f"AI categorisation failed: {e}")
                return
            st.session_state["viz_upload_review_df"] = categorized_df
            st.session_state["viz_upload_dialog_open"] = True
            st.rerun()
        return

    st.caption("Review and adjust categories before saving.")
    display_df = review_df.copy()
    if "date" in display_df.columns:
        display_df["date"] = pd.to_datetime(display_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    edited_df = st.data_editor(
        display_df,
        column_config={
            "category": st.column_config.SelectboxColumn("Category", options=VALID_CATEGORIES, required=True),
            "date": st.column_config.TextColumn("Date", disabled=True),
            "description": st.column_config.TextColumn("Description", disabled=True),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f", disabled=True),
            "bank": st.column_config.TextColumn("Bank", disabled=True),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="viz_review_editor",
    )

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("Save Reviewed Transactions", type="primary", key="viz_save_reviewed"):
            count = save_transactions(edited_df, user_email=user_email)
            st.success(f"Saved {count} transaction(s). Refreshing insights...")
            st.session_state.pop("viz_upload_dialog_open", None)
            st.session_state.pop("viz_upload_review_df", None)
            st.session_state.pop("hist_df", None)
            st.session_state.pop("hist_date_range", None)
            st.rerun()
    with action_col2:
        if st.button("Discard Review", key="viz_discard_review"):
            st.session_state.pop("viz_upload_dialog_open", None)
            st.session_state.pop("viz_upload_review_df", None)
            st.rerun()


# ── Entry point ────────────────────────────────────────────────────────────

st.markdown(_KPI_CSS, unsafe_allow_html=True)
_render_account_top_right(current_user_email)

st.markdown("### Historical Cash Flow Dashboard")
st.caption("Pick a date range to refresh your dashboard, or upload statements for new entries.")

date_col1, date_col2 = st.columns(2)
default_start = date.today() - timedelta(days=365)
with date_col1:
    hist_start = st.date_input("From", value=default_start, key="hist_start")
with date_col2:
    hist_end = st.date_input("To", value=date.today(), key="hist_end")
st.caption("Need more data in this window? Use Upload Statement PDF to import new statements.")
apply_filter_clicked = st.button("Apply Date Filter", type="primary")

if st.button("Upload Statement PDF", type="primary"):
    _open_upload_dialog()
_maybe_open_upload_dialog(current_user_email)

# Clear cached data if date range has changed
cached_range = st.session_state.get("hist_date_range")
current_range = (str(hist_start), str(hist_end))
if cached_range and cached_range != current_range:
    st.session_state.pop("hist_df", None)
    st.session_state.pop("hist_date_range", None)
    st.session_state.pop("hist_needs_load", None)

if hist_start > hist_end:
    st.error("'From' date must be before 'To' date.")
else:
    if "hist_needs_load" not in st.session_state:
        st.session_state["hist_needs_load"] = True
    if apply_filter_clicked:
        st.session_state["hist_needs_load"] = True

    cached_range = st.session_state.get("hist_date_range")
    current_range = (str(hist_start), str(hist_end))
    if cached_range != current_range:
        st.session_state.pop("hist_df", None)
        st.session_state["hist_needs_load"] = True

    if st.session_state.get("hist_needs_load", False):
        try:
            st.session_state["hist_df"] = get_transactions_by_date_range(
                str(hist_start),
                str(hist_end),
                user_email=current_user_email,
            )
            st.session_state["hist_date_range"] = current_range
            st.session_state["hist_needs_load"] = False
        except ValueError as e:
            st.error(f"Configuration error: {e}")
        except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
            st.error(f"Failed to load data: {e}")

    if "hist_df" in st.session_state:
        hist_df = st.session_state["hist_df"]
        if hist_df.empty:
            st.info("No transactions found in the last year.")
        else:
            show_mongodb_dashboard(hist_df)
