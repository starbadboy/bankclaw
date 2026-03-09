from datetime import date, timedelta
from html import escape
from pathlib import Path
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from dotenv import load_dotenv
from streamlit_plotly_events import plotly_events

from webapp.auth import clear_auth_query_token, require_authentication
from webapp.categorizer import VALID_CATEGORIES, categorize_transactions
from webapp.constants import SUPPORTED_BANKS
from webapp.helpers import create_df
from webapp.visualizations_helpers import compute_category_expenses, compute_monthly_cash_flow
from webapp.repository import get_transactions_by_date_range, save_category_memory, save_transactions
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
_DARK_CHART_BG = "#09111f"
_DARK_GRID = "#1f3047"

def _get_manual_category_changes(original_df: pd.DataFrame, edited_df: pd.DataFrame) -> pd.DataFrame:
    changed_rows = edited_df.loc[edited_df["category"] != original_df["category"]].copy()
    if changed_rows.empty:
        return changed_rows
    return changed_rows[["description", "category"]].copy()


_KPI_CSS = """
<style>
div[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top right, rgba(47, 107, 255, 0.18), transparent 28%),
        radial-gradient(circle at top left, rgba(0, 214, 201, 0.10), transparent 26%),
        linear-gradient(180deg, #071120 0%, #0a1628 52%, #0d1b30 100%);
}
.viz-shell {
    border: 1px solid rgba(129, 177, 255, 0.16);
    border-radius: 24px;
    padding: 22px 24px;
    margin-bottom: 16px;
    background: linear-gradient(145deg, rgba(8, 18, 36, 0.96), rgba(13, 27, 48, 0.92));
    box-shadow: 0 24px 64px rgba(2, 6, 23, 0.42);
}
.viz-shell h2 {
    margin: 0 0 6px 0;
    color: #f8fbff;
    font-size: 1.8rem;
}
.viz-shell p {
    margin: 0;
    color: #bcd2f7;
}
.viz-toolbar-shell,
.insights-shell {
    background: linear-gradient(145deg, rgba(8, 18, 36, 0.96), rgba(13, 27, 48, 0.92));
    border: 1px solid rgba(129, 177, 255, 0.16);
    border-radius: 20px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.viz-toolbar-shell {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: end;
}
.viz-toolbar-shell strong {
    display: block;
    margin-bottom: 6px;
    color: #7dd3fc;
    font-size: 0.76rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
}
.viz-toolbar-shell h3 {
    margin: 0;
    color: #f8fbff;
    font-size: 1.25rem;
}
.viz-toolbar-shell span {
    color: #91a7cf;
    font-size: 0.9rem;
}
.viz-filter-shell,
.insights-filter-shell {
    border: 1px solid rgba(129, 177, 255, 0.16);
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(13, 25, 46, 0.92), rgba(9, 18, 34, 0.90));
    padding: 14px 16px 6px 16px;
    margin-bottom: 14px;
}
.viz-control-shell,
.insights-control-shell {
    border: 1px solid rgba(82, 132, 255, 0.20);
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(13, 25, 46, 0.92), rgba(9, 18, 34, 0.90));
    padding: 14px 16px 12px 16px;
    margin-bottom: 16px;
}
.viz-section-shell,
.insights-section-shell {
    border: 1px solid rgba(129, 177, 255, 0.14);
    background: linear-gradient(180deg, rgba(13, 25, 46, 0.88), rgba(9, 18, 34, 0.92));
    border-radius: 18px;
    padding: 14px 16px 8px 16px;
    margin-top: 14px;
}
.insights-section-shell h3 {
    margin: 0 0 4px 0;
    color: #f8fbff;
    font-size: 1.05rem;
}
.insights-section-shell p {
    margin: 0;
    color: #8da6d1;
    font-size: 0.9rem;
}
.viz-chart-shell,
.insights-chart-shell {
    border: 1px solid rgba(129, 177, 255, 0.12);
    border-radius: 18px;
    padding: 12px 12px 4px 12px;
    background: linear-gradient(180deg, rgba(6, 13, 26, 0.86), rgba(10, 19, 36, 0.92));
}
.kpi-card {
    background: linear-gradient(180deg, rgba(13, 25, 46, 0.95), rgba(9, 18, 34, 0.90));
    border: 1px solid rgba(129, 177, 255, 0.14);
    border-radius: 18px;
    padding: 18px 12px;
    text-align: center;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
.kpi-label {
    font-size: 11px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #8da6d1;
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
.category-detail-panel {
    border: 1px solid #dbeafe;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
}
.category-detail-panel h4 {
    margin: 0 0 6px 0;
    color: #0f172a;
    font-size: 1rem;
}
.category-detail-panel p {
    margin: 0 0 12px 0;
    color: #64748b;
    font-size: 0.9rem;
}
.category-detail-item {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 0;
    border-top: 1px solid #e2e8f0;
}
.category-detail-item:first-of-type {
    border-top: none;
}
.category-detail-item-main {
    min-width: 0;
}
.category-detail-item-description {
    color: #0f172a;
    font-weight: 600;
}
.category-detail-item-meta {
    color: #64748b;
    font-size: 0.85rem;
}
.category-detail-item-amount {
    color: #F63366;
    font-weight: 700;
    white-space: nowrap;
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
        line={"color": "#7dd3fc", "width": 3},
        hovertext=[f"${v:,.0f}" for v in monthly["Net"]],
        hoverinfo=_HOVERINFO_TEXT_NAME,
    )
    layout = go.Layout(
        title="Monthly Cash Flow",
        title_font={"size": 20},
        xaxis={"title": "Month", "showgrid": False, "dtick": "M1"},
        yaxis={
            "showgrid": True,
            "gridcolor": _DARK_GRID,
            "zeroline": True,
            "zerolinecolor": "#29415f",
            "zerolinewidth": 2,
            "tickformat": "$,.1s",
            "color": "#c8daf8",
        },
        barmode="relative",
        hovermode="x unified",
        bargap=0.5,
        showlegend=True,
        legend={"orientation": "h", "y": 1.12, "x": 0.01, "font": {"color": "#c8daf8"}},
        font={"color": "#e5f0ff"},
        plot_bgcolor=_DARK_CHART_BG,
        paper_bgcolor=_DARK_CHART_BG,
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
                "gridcolor": _DARK_GRID,
                "zeroline": True,
                "zerolinecolor": "#29415f",
                "zerolinewidth": 2,
                "tickformat": "$,.1s",
                "color": "#c8daf8",
            },
            bargap=0.5,
            font={"color": "#e5f0ff"},
            plot_bgcolor=_DARK_CHART_BG,
            paper_bgcolor=_DARK_CHART_BG,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_category_donut(cat_expenses: pd.Series) -> list[dict]:
    labels = cat_expenses.index.tolist()
    values = cat_expenses.astype(float).tolist()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
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
            font={"color": "#e5f0ff"},
            plot_bgcolor=_DARK_CHART_BG,
            paper_bgcolor=_DARK_CHART_BG,
        ),
    )
    return plotly_events(
        fig,
        click_event=True,
        hover_event=True,
        key="category_breakdown_chart",
    )


def _get_top_category_transactions(df: pd.DataFrame, selected_category: str) -> pd.DataFrame:
    filtered = df.loc[(df["category"] == selected_category) & (df["amount"] < 0)].copy()
    if filtered.empty:
        return filtered
    filtered["_abs_amount"] = filtered["amount"].abs()
    return (
        filtered.sort_values("_abs_amount", ascending=False)
        .head(10)
        .drop(columns="_abs_amount")
    )


def _get_selected_category_from_points(cat_expenses: pd.Series, chart_points: list[dict]) -> str | None:
    if not isinstance(chart_points, list) or not chart_points:
        return None
    point = chart_points[0]
    if not isinstance(point, dict):
        return None

    labels = cat_expenses.index.tolist()
    label = point.get("label")
    if isinstance(label, str) and label in labels:
        return label

    for index_key in ("pointNumber", "pointIndex"):
        selected_index = point.get(index_key)
        if isinstance(selected_index, int) and 0 <= selected_index < len(labels):
            return str(labels[selected_index])

    return None


def _get_selected_category() -> str | None:
    stored_category = st.session_state.get("category_breakdown_selected_category")
    return stored_category if isinstance(stored_category, str) else None


def _render_category_detail_panel(df: pd.DataFrame, selected_category: str) -> None:
    top_transactions = _get_top_category_transactions(df, selected_category)
    safe_selected_category = escape(selected_category)
    detail_items = []
    for row in top_transactions.itertuples(index=False):
        txn_date = pd.to_datetime(row.date, errors="coerce")
        formatted_date = txn_date.strftime("%Y-%m-%d") if not pd.isna(txn_date) else ""
        safe_description = escape(str(row.description))
        safe_bank = escape(str(row.bank))
        safe_date = escape(formatted_date)
        detail_items.append(
            (
                '<div class="category-detail-item">'
                '<div class="category-detail-item-main">'
                f'<div class="category-detail-item-description">{safe_description}</div>'
                f'<div class="category-detail-item-meta">{safe_date} • {safe_bank}</div>'
                "</div>"
                f'<div class="category-detail-item-amount">-${abs(row.amount):,.2f}</div>'
                "</div>"
            )
        )

    if not detail_items:
        detail_items.append(
            (
                '<div class="category-detail-item">'
                '<div class="category-detail-item-main">'
                '<div class="category-detail-item-description">No expense transactions found.</div>'
                "</div>"
                "</div>"
            )
        )

    st.markdown(
        (
            '<div class="category-detail-panel">'
            f"<h4>Top 10 Transactions in {safe_selected_category}</h4>"
            "<p>Largest expense transactions for the selected category.</p>"
            f"{''.join(detail_items)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _show_category_breakdown(df: pd.DataFrame, cat_expenses: pd.Series) -> None:
    st.markdown(
        """
        <div class="insights-section-shell">
            <h3>Category Breakdown</h3>
            <p>See where spending concentration is highest by category.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    excluded_categories = st.multiselect(
        "Exclude categories",
        options=cat_expenses.index.tolist(),
        default=[],
        help="Hide selected categories from the Category Breakdown chart.",
        key="category_breakdown_excluded_categories",
    )
    filtered_cat_expenses = cat_expenses[~cat_expenses.index.isin(excluded_categories)]
    selected_category = _get_selected_category()
    show_detail_panel = bool(selected_category and selected_category in filtered_cat_expenses.index)

    if show_detail_panel:
        chart_col, detail_col = st.columns([3, 2])
    else:
        chart_col = st.container()
        detail_col = None

    chart_points = []
    with chart_col:
        st.markdown('<div class="insights-chart-shell">', unsafe_allow_html=True)
        if filtered_cat_expenses.empty:
            st.info("No categories left to display. Clear one or more exclusions.")
        else:
            chart_points = _show_category_donut(filtered_cat_expenses)
        st.markdown(_HTML_DIV_CLOSE, unsafe_allow_html=True)

    selected_from_points = _get_selected_category_from_points(filtered_cat_expenses, chart_points)
    if selected_from_points is not None and selected_from_points != selected_category:
        st.session_state["category_breakdown_selected_category"] = selected_from_points
        st.rerun()

    if show_detail_panel and detail_col is not None:
        with detail_col:
            _render_category_detail_panel(df, selected_category)


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
            _show_category_breakdown(df, cat_expenses)


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
                        categorized_df = categorize_transactions(raw_df, user_email=user_email)
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
            try:
                count = save_transactions(edited_df, user_email=user_email)
            except ValueError as e:
                st.error(f"Configuration error: {e}")
                return
            except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
                st.error(f"Failed to save reviewed transactions: {e}")
                return

            manual_changes = _get_manual_category_changes(display_df, edited_df)
            if not manual_changes.empty:
                try:
                    save_category_memory(manual_changes, user_email=user_email, source="manual")
                except Exception as e:  # pylint: disable=broad-except  # noqa: BLE001
                    st.warning(f"Transactions were saved, but category memory could not be updated: {e}")

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

st.markdown(
    """
    <section class="viz-shell">
        <div class="viz-toolbar-shell">
            <div>
                <strong>Insights Workspace</strong>
                <h3>Historical Cash Flow Dashboard</h3>
                <span>Track cash movement, category concentration, and upload fresh statements without leaving the dashboard.</span>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="viz-control-shell insights-control-shell">
        <strong style="display:block; margin-bottom:6px; color:#7dd3fc; letter-spacing:0.18em; text-transform:uppercase; font-size:0.74rem;">Dashboard Controls</strong>
        <p style="margin:0; color:#8da6d1;">Adjust the reporting window or import more statements to refresh the analytics below.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
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
