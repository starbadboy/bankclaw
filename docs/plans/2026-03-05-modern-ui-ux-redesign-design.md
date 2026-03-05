# Modern UI/UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Streamlit experience to feel modern and user-friendly while preserving existing auth, parsing, categorization, and history capabilities.

**Architecture:** Introduce a reusable visual style system and guided workflow presentation in the main app first, then apply consistent design language to insights/history pages in small phases. Keep business logic unchanged; focus on UX flow clarity, layout hierarchy, and feedback states.

**Tech Stack:** Python 3.12, Streamlit, Plotly, pytest

---

## Task 1: Main App Visual Foundation + Guided Flow (TDD)

**Files:**

- Modify: `tests/test_app.py`
- Modify: `webapp/app.py`

**Steps:**

1. Add failing tests for new UI helper render calls (hero/workflow/status) and unchanged core flow behavior.
2. Run focused tests and verify failing assertions match missing UI helper behavior.
3. Implement minimal styling + workflow UI helpers in `webapp/app.py`.
4. Re-run focused tests until green.

---

## Task 2: Global Theme Tokens

**Files:**

- Modify: `.streamlit/config.toml`

**Steps:**

1. Update Streamlit theme tokens for modern visual baseline.
2. Run app smoke test (`pytest tests/test_app.py -q`) to ensure no breakage from theme config changes.

---

## Task 3: Visualization Page Redesign

**Files:**

- Modify: `tests/test_visualizations.py`
- Modify: `webapp/pages/1_visualizations.py`

**Steps:**

1. Add tests for new section structure and resilient empty/loading states.
2. Implement modern card sections, improved chart framing, and clearer filter actions.
3. Re-run visualization tests and adjust until green.

---

## Task 4: History Page UX Refresh

**Files:**

- Modify: `webapp/pages/3_history.py`
- Modify: (optional) `tests/e2e/test_auth_dashboard_flow.py` for updated UX checkpoints if necessary

**Steps:**

1. Apply consistent design system from main app.
2. Improve scanability for filters/results/download actions.
3. Verify via existing test flow and update assertions only where intentional UX text changes require it.

---

## Task 5: Validation & Regression Pass

**Files:**

- No production file changes expected unless issues found

**Steps:**

1. Run unit/integration/e2e tests relevant to touched files.
2. Address regressions.
3. Document potential UX risks and follow-up enhancements.
