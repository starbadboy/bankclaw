from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from dotenv import load_dotenv

from webapp.pages.visualizations_helpers import compute_category_expenses, compute_monthly_cash_flow
from webapp.repository import get_transactions_by_date_range

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator


def render_metric(column: "DeltaGenerator", title, value, title_color="#262730", value_color="#262730"):
    column.markdown(
        f"""
        <div style="text-align:center;">
            <div style="font-size:16px; color:{title_color};">{title}</div>
            <div style="font-size:36px; color:{value_color};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_stacked_bar_chart(df: pd.DataFrame):
    income_trace = go.Bar(
        x=df.index,
        y=df["Income"],
        name="Income",
        marker={"color": "#00CEAA", "cornerradius": 10},
        hovertext=[f"${s:,.2f}" for s in df["Income"]],
        hoverinfo="text+name",
        offsetgroup=0,
    )

    expenses_trace = go.Bar(
        x=df.index,
        y=[-expense for expense in df["Expenses"]],
        name="Expenses",
        marker={"color": "#F63366", "cornerradius": 10},
        hovertext=[f"${s:,.2f}" for s in df["Expenses"]],
        hoverinfo="text+name",
        offsetgroup=0,
    )

    savings_trace = go.Scatter(
        x=df.index,
        y=df["Income"] - df["Expenses"],
        name="Savings",
        mode="lines",
        line={"color": "black", "width": 4},
        hoverinfo="text+name",
        text=[f"${s:,.2f}" for s in df["amount"]],
    )

    layout = go.Layout(
        title="Cash Flow",
        title_font={"size": 26},
        xaxis={"title": "Month", "showgrid": False, "dtick": "M1"},
        yaxis={
            "title": "Amount",
            "showgrid": False,
            "zeroline": True,
            "zerolinecolor": "#EFEFEF",
            "zerolinewidth": 2,
            "tickformat": "$,.1s",
        },
        barmode="relative",
        hovermode="x unified",
        bargap=0.5,
        showlegend=False,
    )

    fig = go.Figure(data=[income_trace, expenses_trace, savings_trace], layout=layout)
    chart = st.plotly_chart(fig, use_container_width=True)

    total_income = round(df["Income"].sum())
    total_expenses = round(df["Expenses"].sum())
    total_savings = round(df["amount"].sum())

    # Avoid division by zero
    savings_rate = total_savings / total_income * 100 if total_income > 0 else 0
    formatted_savings_rate = f"{savings_rate:.2f}%"
    formatted_total_savings = f"${total_savings:,.0f}"
    formatted_total_savings = f"-${abs(total_savings):,}" if total_savings < 0 else f"${total_savings:,}"

    col1, col2, col3, col4 = st.columns(4)

    if chart:
        render_metric(col1, "Income", f"${total_income:,}", value_color="#00CEAA")
        render_metric(col2, "Expenses", f"${total_expenses:,}", value_color="#F63366")
        render_metric(col3, "Total Savings", formatted_total_savings)
        render_metric(col4, "Savings Rate", formatted_savings_rate)


st.markdown("# Visualizations")

if "df" in st.session_state:
    df: pd.DataFrame = st.session_state["df"].copy()
    df.index = pd.to_datetime(df["date"])
    df["Bank"] = df["bank"]
    df["Income"] = df["amount"].apply(lambda x: max(0, x))
    df["Expenses"] = df["amount"].apply(lambda x: abs(x) if x < 0 else 0)
    df = df.drop(columns=["description", "date"])
    df = df.resample("MS").sum()

    show_stacked_bar_chart(df)

if "df" not in st.session_state:
    switch_page_button = st.button("Convert a bank statement")
    if switch_page_button:
        st.switch_page("app.py")


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
        hoverinfo="text+name",
    )
    expense_bar = go.Bar(
        x=monthly.index,
        y=[-v for v in monthly["Expenses"]],
        name="Expenses",
        marker={"color": "#F63366", "cornerradius": 8},
        hovertext=[f"${v:,.0f}" for v in monthly["Expenses"]],
        hoverinfo="text+name",
    )
    net_line = go.Scatter(
        x=monthly.index,
        y=monthly["Net"],
        name="Net",
        mode="lines+markers",
        line={"color": "#262730", "width": 3},
        hovertext=[f"${v:,.0f}" for v in monthly["Net"]],
        hoverinfo="text+name",
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
                hoverinfo="text+name",
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

st.divider()
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
            hist_df = get_transactions_by_date_range(str(hist_start), str(hist_end))
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
