from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from dotenv import load_dotenv

from webapp.auth import require_authentication
from webapp.pages.visualizations_helpers import compute_category_expenses, compute_monthly_cash_flow
from webapp.repository import get_transactions_by_date_range

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

_KPI_CSS = """
<style>
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
        title_font={"size": 22},
        xaxis={"title": "Month", "showgrid": False, "dtick": "M1"},
        yaxis={
            "showgrid": False,
            "zeroline": True,
            "zerolinecolor": "#EFEFEF",
            "zerolinewidth": 2,
            "tickformat": "$,.1s",
        },
        barmode="relative",
        hovermode="x unified",
        bargap=0.5,
        showlegend=True,
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
            title_font={"size": 22},
            xaxis={"showgrid": False, "dtick": "M1"},
            yaxis={
                "showgrid": False,
                "zeroline": True,
                "zerolinecolor": "#EFEFEF",
                "zerolinewidth": 2,
                "tickformat": "$,.1s",
            },
            bargap=0.5,
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
        layout=go.Layout(title="Expenses by Category", title_font={"size": 22}, showlegend=False),
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

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    _show_cash_flow_chart(monthly)

    col_left, col_right = st.columns(2)
    with col_left:
        _show_pl_chart(monthly)
    with col_right:
        if not cat_expenses.empty:
            _show_category_donut(cat_expenses)


# ── Entry point ────────────────────────────────────────────────────────────

st.markdown("## Historical Cash Flow Dashboard")
st.caption("Sourced from transactions saved to MongoDB.")

date_col1, date_col2 = st.columns(2)
with date_col1:
    hist_start = st.date_input("From", value=date.today() - timedelta(days=30), key="hist_start")
with date_col2:
    hist_end = st.date_input("To", value=date.today(), key="hist_end")

# Clear cached data if date range has changed
cached_range = st.session_state.get("hist_date_range")
current_range = (str(hist_start), str(hist_end))
if cached_range and cached_range != current_range:
    st.session_state.pop("hist_df", None)
    st.session_state.pop("hist_date_range", None)

if hist_start > hist_end:
    st.error("'From' date must be before 'To' date.")
else:
    if st.button("Load Historical Data", type="secondary"):
        try:
            hist_df = get_transactions_by_date_range(
                str(hist_start),
                str(hist_end),
                user_email=current_user_email,
            )
            if hist_df.empty:
                st.info("No transactions found for the selected date range.")
                st.session_state.pop("hist_df", None)
                st.session_state.pop("hist_date_range", None)
            else:
                st.session_state["hist_df"] = hist_df
                st.session_state["hist_date_range"] = current_range
                st.rerun()
        except ValueError as e:
            st.error(f"Configuration error: {e}")
        except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
            st.error(f"Failed to load data: {e}")

    if "hist_df" in st.session_state:
        show_mongodb_dashboard(st.session_state["hist_df"])
