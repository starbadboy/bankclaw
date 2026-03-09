# Dashboard Style Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restyle the Streamlit app to follow a dark, premium dashboard aesthetic inspired by the provided reference image while preserving existing product behavior.

**Architecture:** Introduce a reusable dark visual language first in the main app, then extend it page by page so the visualizations and history experiences share the same spacing, card framing, action styling, and chart palette. Keep business logic unchanged unless tests require minor UI helper refactors to make the new presentation testable.

**Tech Stack:** Python 3.12, Streamlit, Plotly, pytest, unittest.mock

---

### Task 1: Main App Dark Foundation

**Files:**
- Modify: `tests/test_app.py`
- Modify: `webapp/app.py`

**Step 1:** Write a failing unit test for the new dashboard-style CSS and hero copy.

```python
def test_inject_modern_css_renders_dashboard_tokens():
    mock_st = MagicMock()

    with patch("webapp.app.st", mock_st):
        from webapp.app import _inject_modern_css
        _inject_modern_css()

    rendered = mock_st.markdown.call_args[0][0]
    assert ".ss-shell" in rendered
    assert ".ss-kpi-card" in rendered
```

**Step 2:** Run the focused app test to verify it fails for the expected missing selectors.

Run: `pytest tests/test_app.py::test_inject_modern_css_renders_dashboard_tokens -q`

Expected: FAIL because the new dark dashboard selectors are not present yet.

**Step 3:** Write a failing unit test for the upgraded hero panel.

```python
def test_render_hero_uses_dashboard_message():
    mock_st = MagicMock()

    with patch("webapp.app.st", mock_st):
        from webapp.app import _render_hero
        _render_hero()

    rendered = " ".join(call.args[0] for call in mock_st.markdown.call_args_list if call.args)
    assert "Control your statement workflow" in rendered
```

**Step 4:** Run the focused hero test to verify it fails for the expected missing copy.

Run: `pytest tests/test_app.py::test_render_hero_uses_dashboard_message -q`

Expected: FAIL because the existing hero still renders the old copy.

**Step 5:** Implement the minimal `webapp/app.py` CSS and hero markup needed to satisfy both tests.

```python
def _inject_modern_css() -> None:
    st.markdown(_MODERN_UI_CSS, unsafe_allow_html=True)


def _render_hero() -> None:
    st.markdown(
        """
        <section class="ss-shell">
            <div class="ss-hero">
                <p class="ss-eyebrow">Statement Intelligence</p>
                <h2>Control your statement workflow</h2>
                <p>Upload, categorise, review, and explore transactions in a dashboard that feels calm and high-signal.</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
```

**Step 6:** Run the focused tests to verify they pass.

Run: `pytest tests/test_app.py::test_inject_modern_css_renders_dashboard_tokens tests/test_app.py::test_render_hero_uses_dashboard_message -q`

Expected: PASS

---

### Task 2: Main App Workflow + Auth Shell

**Files:**
- Modify: `tests/test_app.py`
- Modify: `webapp/app.py`

**Step 1:** Write a failing test for a more polished workflow strip using dashboard card classes.

```python
def test_render_workflow_uses_dashboard_cards():
    mock_st = MagicMock()

    with patch("webapp.app.st", mock_st):
        from webapp.app import _render_workflow
        _render_workflow(has_df=False, has_categorized=False)

    rendered = " ".join(call.args[0] for call in mock_st.markdown.call_args_list if call.args)
    assert "ss-workflow-card" in rendered
```

**Step 2:** Run the focused workflow test to verify it fails for the expected missing class.

Run: `pytest tests/test_app.py::test_render_workflow_uses_dashboard_cards -q`

Expected: FAIL because the current workflow uses pill markup only.

**Step 3:** Implement the minimal workflow and auth container updates in `webapp/app.py`.

```python
def _render_workflow(*, has_df: bool, has_categorized: bool) -> None:
    # render workflow cards with current-state emphasis


def _show_auth_screen() -> None:
    # wrap login and register sections in a dashboard shell
```

**Step 4:** Run the focused app tests to verify the helper behavior stays green.

Run: `pytest tests/test_app.py -q`

Expected: PASS

---

### Task 3: Visualizations Page Dashboard Layout

**Files:**
- Modify: `tests/test_visualizations.py`
- Modify: `webapp/pages/1_visualizations.py`

**Step 1:** Write failing unit tests for the top shell, KPI framing, and dark chart theme behavior.

**Step 2:** Run the focused visualization tests and verify they fail for the expected missing classes or layout markers.

Run: `pytest tests/test_visualizations.py -q`

Expected: FAIL due to missing redesigned shell markers.

**Step 3:** Implement the minimal dark dashboard framing, KPI cards, filter shell, and Plotly palette adjustments in `webapp/pages/1_visualizations.py`.

**Step 4:** Run the focused visualization tests to verify they pass.

Run: `pytest tests/test_visualizations.py -q`

Expected: PASS

---

### Task 4: History Page Dashboard Layout

**Files:**
- Modify: `tests/test_history.py`
- Modify: `webapp/pages/3_history.py`

**Step 1:** Write failing unit tests for dashboard-style filter panels, action framing, and dark results presentation.

**Step 2:** Run the focused history tests and verify they fail for the expected missing UI markers.

Run: `pytest tests/test_history.py -q`

Expected: FAIL due to missing redesigned shell markers.

**Step 3:** Implement the minimal history-page shell, filter cards, action area, and dark data-editor framing in `webapp/pages/3_history.py`.

**Step 4:** Run the focused history tests to verify they pass.

Run: `pytest tests/test_history.py -q`

Expected: PASS

---

### Task 5: Theme Token Finalization

**Files:**
- Modify: `.streamlit/config.toml`

**Step 1:** Update the Streamlit theme tokens to align with the dark dashboard palette.

```toml
[theme]
primaryColor="#2F6BFF"
backgroundColor="#071120"
secondaryBackgroundColor="#0D1A2B"
textColor="#E5F0FF"
```

**Step 2:** Run the app smoke test to verify the theme change does not break existing app tests.

Run: `pytest tests/test_app.py -q`

Expected: PASS

---

### Task 6: Verification

**Files:**
- Verify: `webapp/app.py`
- Verify: `webapp/pages/1_visualizations.py`
- Verify: `webapp/pages/3_history.py`
- Verify: `.streamlit/config.toml`

**Step 1:** Run the focused UI-related test files.

Run: `pytest tests/test_app.py tests/test_visualizations.py tests/test_history.py -q`

Expected: PASS

**Step 2:** Run lints for edited files and fix any introduced issues.

Run: `ruff check webapp/app.py webapp/pages/1_visualizations.py webapp/pages/3_history.py tests/test_app.py tests/test_visualizations.py tests/test_history.py`

Expected: PASS

**Step 3:** Run code review before closing the work.

Run: `/code-review`

Expected: review completed or findings addressed.
