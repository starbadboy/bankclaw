# Category Top Transactions Popup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let users click a category in the donut chart and see a floating-style detail panel beside the chart showing the top 10 largest transactions for that category.

**Architecture:** Keep the existing donut chart in `webapp/pages/1_visualizations.py` and add a right-side detail panel rendered from the currently selected category. The interaction stays within Streamlit and Plotly by using chart selection state plus `st.session_state`, while hover remains the built-in Plotly tooltip.

**Tech Stack:** Python 3.12, Streamlit 1.46, Plotly 6, pandas, pytest, unittest.mock

---

### Task 1: Category Detail Panel Interaction

**Files:**
- Modify: `webapp/pages/1_visualizations.py`
- Test: `tests/test_visualizations.py`

**Step 1: Write the failing test**

Add a test in `tests/test_visualizations.py` that proves the top 10 transactions are filtered to the selected category and sorted by absolute amount descending.

```python
def test_get_top_category_transactions_returns_top_10_largest_for_selected_category():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"
    food_rows = [
        {
            "date": f"2024-01-{day:02d}",
            "description": f"FOOD {day}",
            "amount": -(day * 10.0),
            "bank": "DBS",
            "category": "Food & Dining",
        }
        for day in range(1, 13)
    ]
    df = pd.DataFrame(food_rows + [
        {"date": "2024-02-01", "description": "GRAB", "amount": -20.0, "bank": "DBS", "category": "Transport"},
    ])

    module_globals = runpy.run_path(str(page_path))
    result = module_globals["_get_top_category_transactions"](df, "Food & Dining")

    assert len(result) == 10
    assert result["category"].eq("Food & Dining").all()
    assert result["amount"].tolist() == [-120.0, -110.0, -100.0, -90.0, -80.0, -70.0, -60.0, -50.0, -40.0, -30.0]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_visualizations.py::test_get_top_category_transactions_returns_top_10_largest_for_selected_category -v`

Expected: FAIL with a missing helper such as `KeyError` or `_get_top_category_transactions` not existing.

**Step 3: Write minimal implementation**

Add a helper in `webapp/pages/1_visualizations.py`:

```python
def _get_top_category_transactions(df: pd.DataFrame, category: str) -> pd.DataFrame:
    category_df = df.loc[(df["category"] == category) & (df["amount"] < 0)].copy()
    if category_df.empty:
        return category_df
    category_df["amount_abs"] = category_df["amount"].abs()
    category_df = category_df.sort_values(by="amount_abs", ascending=False).head(10)
    return category_df.drop(columns=["amount_abs"])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_visualizations.py::test_get_top_category_transactions_returns_top_10_largest_for_selected_category -v`

Expected: PASS

**Step 5: Write the failing test**

Add a page-level test that proves the donut chart selection shows the category detail panel beside the chart.

```python
def test_show_dashboard_renders_selected_category_top_transactions_panel():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    selected_points = {
        "selection": {
            "points": [{"label": "Food & Dining"}]
        }
    }

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.plotly_chart", return_value=selected_points), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["show_mongodb_dashboard"](make_df())

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert "Top Transactions" in rendered
    assert "Food & Dining" in rendered
```

**Step 6: Run test to verify it fails**

Run: `pytest tests/test_visualizations.py::test_show_dashboard_renders_selected_category_top_transactions_panel -v`

Expected: FAIL because the page does not yet render a detail panel from chart selection.

**Step 7: Write minimal implementation**

Update `webapp/pages/1_visualizations.py` to:
- Render the donut and detail panel in a two-column layout.
- Call `st.plotly_chart(fig, use_container_width=True, on_select="rerun")`.
- Read the selected category label from the returned event object.
- Save the selected category in `st.session_state`.
- Render a styled detail card with the category title and a compact top-transactions table.

Use logic shaped like:

```python
chart_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
selected_points = chart_event.selection.get("points", []) if chart_event else []
if selected_points:
    st.session_state["category_breakdown_selected_category"] = selected_points[0].get("label")
selected_category = st.session_state.get("category_breakdown_selected_category")
```

**Step 8: Run the focused page tests**

Run:
- `pytest tests/test_visualizations.py::test_show_dashboard_renders_selected_category_top_transactions_panel -v`
- `pytest tests/test_visualizations.py::test_show_dashboard_keeps_full_donut_when_no_categories_are_excluded -v`
- `pytest tests/test_visualizations.py::test_show_dashboard_filters_excluded_categories_from_donut_chart -v`

Expected: PASS for all three tests.

**Step 9: Add one empty-state regression test**

Add a test proving no detail panel is shown before any category is selected.

```python
def test_show_dashboard_hides_top_transactions_panel_without_selected_category():
    page_path = Path(__file__).parent.parent / "webapp" / "pages" / "1_visualizations.py"

    with patch("webapp.auth.require_authentication", return_value="demo@example.com"), \
         patch("streamlit.markdown") as markdown_mock, \
         patch("streamlit.caption"), \
         patch("streamlit.columns", side_effect=_columns_factory), \
         patch("streamlit.date_input", side_effect=[date(2024, 1, 1), date(2024, 1, 31)]), \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.multiselect", return_value=[]), \
         patch("streamlit.plotly_chart", return_value={}), \
         patch("webapp.repository.get_transactions_by_date_range", return_value=pd.DataFrame()):
        module_globals = runpy.run_path(str(page_path))
        module_globals["show_mongodb_dashboard"](make_df())

    rendered = " ".join(call.args[0] for call in markdown_mock.call_args_list if call.args)
    assert "Top Transactions" not in rendered
```

**Step 10: Run the targeted test file**

Run: `pytest tests/test_visualizations.py -v`

Expected: PASS

**Step 11: Run lint verification for edited files**

Run: `pytest tests/test_visualizations.py -v && python -m compileall webapp/pages/1_visualizations.py tests/test_visualizations.py`

Expected: all tests pass and compilation succeeds with no syntax errors.
