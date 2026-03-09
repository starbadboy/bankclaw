# Per-User Category Memory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a per-user category memory store that reuses past categories for similar descriptions above 70% and learns only from explicit manual category changes.

**Architecture:** MongoDB gets a dedicated `category_memory` collection keyed by `user_email` and `normalized_description`. Upload categorization will consult this memory first, apply exact or fuzzy matches, and only send unmatched rows to AI. Manual category edits from upload review and history will upsert memory records so future uploads can reuse them.

**Tech Stack:** Python 3.12, pandas, pymongo, Streamlit, pytest, unittest.mock, difflib

---

### Task 1: Category Memory Repository

**Files:**
- Modify: `webapp/repository.py`
- Test: `tests/integration/test_user_repository.py`

**Step 1:** Write failing integration tests for saving and reading `category_memory` records.

**Step 2:** Run the targeted integration tests and verify the new tests fail for missing functions.

**Step 3:** Add minimal repository functions and indexes for `category_memory`.

**Step 4:** Run the targeted integration tests and verify they pass.

---

### Task 2: Memory-First Categorization Logic

**Files:**
- Modify: `webapp/categorizer.py`
- Test: `tests/test_categorizer.py`

**Step 1:** Write failing unit tests for normalization, exact match reuse, fuzzy match reuse at 70%, and AI fallback for unmatched rows.

**Step 2:** Run the targeted unit tests and verify they fail for the expected missing behavior.

**Step 3:** Implement the smallest categorization changes needed to make the tests pass.

**Step 4:** Run the targeted unit tests and verify they pass.

---

### Task 3: Upload Flow Manual Memory Learning

**Files:**
- Modify: `webapp/pages/1_visualizations.py`
- Test: `tests/test_visualizations.py`

**Step 1:** Write failing tests covering upload review using memory-aware categorization and saving memory only for rows manually changed from the AI result.

**Step 2:** Run the targeted tests and verify they fail for missing behavior.

**Step 3:** Implement the minimal upload-flow wiring for memory lookup and manual-change persistence.

**Step 4:** Run the targeted tests and verify they pass.

---

### Task 4: History Manual Edits Update Memory

**Files:**
- Modify: `webapp/pages/3_history.py`
- Test: `tests/test_history.py`

**Step 1:** Write failing tests proving history category edits also upsert per-user memory.

**Step 2:** Run the targeted tests and verify they fail for missing behavior.

**Step 3:** Implement the minimal history-page wiring needed to persist manual edits to memory.

**Step 4:** Run the targeted tests and verify they pass.

---

### Task 5: Verification

**Files:**
- Verify: `webapp/repository.py`
- Verify: `webapp/categorizer.py`
- Verify: `webapp/pages/1_visualizations.py`
- Verify: `webapp/pages/3_history.py`

**Step 1:** Run the focused test files for repository, categorizer, visualizations, and history.

**Step 2:** Run lint checks for edited files and fix any introduced issues.

**Step 3:** Run code review before closing out the work.
