# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Statement Sensei converts bank statement PDFs to CSVs using the [`monopoly-core`](https://github.com/benjamin-awd/monopoly) library. Available as a hosted Streamlit web app and an offline desktop app built with Tauri. Supports 18+ banks.

## Commands

```bash
# Start dev server
./start.sh
# or manually:
uv venv && uv sync --group dev
uv run streamlit run webapp/app.py

# Run all tests
uv run pytest .

# Run a single test file
uv run pytest tests/test_app.py

# Run a single test
uv run pytest tests/test_app.py::test_name

# Lint / format
uv run ruff check .
uv run ruff format .
uv run isort .

# Build desktop app
cd tauri && npm install && npm run tauri build

# Build installable binary (PyInstaller)
pyinstaller entrypoint.spec

# Docker
docker compose up
```

System dependencies required: `poppler`, `ocrmypdf` (via `brew install poppler ocrmypdf` or `apt-get`).

## Architecture

### Web App (`webapp/`)

Flat module layout — no deep package hierarchy:

- `app.py` — Streamlit entry point, UI orchestration, session state management (~1400 lines)
- `helpers.py` — Core business logic: `parse_bank_statement()`, `build_pipeline()`, `create_df()`, `categorize_and_save_df()`
- `models.py` — Dataclass models: `ProcessedFile`, `TransactionMetadata`, `CategorizedTransaction`
- `auth.py` — HMAC-SHA256 JWT-like tokens, Google OAuth via Authlib
- `repository.py` — MongoDB batch upserts for transactions, category memory, custom categories
- `user_repository.py` — User profile management
- `db.py` — Lazy MongoClient singleton
- `categorizer.py` — AI transaction categorization (OpenAI/DeepSeek) with MongoDB-backed memory
- `category_definitions.py` — Category name mappings
- `constants.py` — App-wide constants and supported bank info
- `pages/1_visualizations.py` — Cash flow dashboards (plotly)
- `pages/3_history.py` — Transaction history, filtering, deletion, CSV export

### Data Flow

1. User uploads PDF → `parse_bank_statement()` detects bank via Monopoly's `BankDetector`
2. Falls back to `GenericBank` if unrecognized (user sees a warning)
3. Pipeline extracts transactions; OCR applied if PDF has no text layer
4. `create_df()` merges multiple uploads into a single DataFrame
5. Optional AI categorization via `categorizer.py` (requires `OPENAI_API_KEY`)
6. MongoDB save with duplicate-safe upserts (unique index: user_email + date + description + amount + bank)

### Desktop App (`tauri/`)

Tauri 2.0 (Rust) wraps the PyInstaller binary in a WebView. `entrypoint.py` is the PyInstaller entry point that starts the embedded Streamlit server.

### Testing (`tests/`)

- `unit/` — Function-level tests with `unittest.mock`
- `integration/` — Repository/DB-level tests
- `e2e/` — User story spec tests
- `fixtures/` — Real PDF and CSV files for parsing tests

Always check existing test structure and patterns before creating new tests.

## Key Constraints

- **No Windows support** — upstream `pdftotext` build issues
- **Stateless by default** — MongoDB features are optional (enabled via env vars)
- **PDF_PASSWORDS** env var accepts a JSON array: `'["pass1", "pass2"]'`
- When changing authentication/session behavior, verify it works consistently across all Streamlit pages, not just the entry page

## Code Style

- Line length: 120 characters
- Formatter: `ruff-format` (black-compatible)
- Linter: `ruff` + `pylint`
- Imports: `isort` with black profile
- Naming: `snake_case` functions/variables, `PascalCase` classes
- Pre-commit hooks enforce formatting automatically (run `pre-commit install`)

## Agent Working Rules

1. Before writing code, describe the solution and wait for approval. Ask clarifying questions if requirements are unclear.
2. If a task requires modifying 3+ files, stop and break it into smaller tasks first.
3. After writing code, list potential issues and suggest test cases.
4. When finding a bug, write a failing test first, then iterate until it passes.
5. If a task requires database schema changes (stored procedures, migrations), stop and ask the user before proceeding.
6. When Streamlit OIDC/auth features are involved, verify runtime dependencies (e.g., `Authlib`) up front.
7. The backend may return data as `logs` or `crmlogs` — use the correct property, no fallbacks.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
