# Project Context

## Purpose

Statement Sensei converts bank statement PDFs to CSVs using the [monopoly](https://github.com/benjamin-awd/monopoly) CLI library. Supports 18+ banks (DBS, OCBC, UOB, Maybank, Chase, HSBC, Bank of America, RBC, Scotiabank, TD, etc.). Available as a hosted Streamlit web app and an offline desktop app built with Tauri.

## Tech Stack

- **Language**: Python 3.10–3.14 (target 3.12)
- **Frameworks**: Streamlit (web app UI), Tauri + Rust (desktop wrapper)
- **Key Library**: `monopoly-core==0.19.6` (bank statement parsing engine)
- **PDF Handling**: `pdftotext`, `pymupdf`, `ocrmypdf`
- **Data**: `pandas`, `plotly`
- **Testing**: `pytest`, `unittest.mock`
- **Build/CI**: `uv` (package manager), `pdm-backend`, `pyinstaller`, GitHub Actions
- **Infrastructure**: Docker (Docker Hub), multi-platform (linux/amd64, linux/arm64, macOS x86/ARM)
- **Key Libraries**: `pydantic` (SecretStr for passwords), `git-cliff` (changelogs)

## Project Conventions

### Code Style

- **Line length**: 120 characters
- **Formatter**: `ruff-format` (black-compatible)
- **Linter**: `ruff` with broad ruleset + `pylint`
- **Imports**: `isort` with black profile
- **Pre-commit hooks**: `ruff-check`, `ruff-format`, `end-of-file-fixer`, `trailing-whitespace`, `cargo-fmt`
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes

### Architecture Patterns

- **Backend**: Flat module layout within `webapp/`
  - `webapp/app.py` — Streamlit entry point and UI orchestration
  - `webapp/helpers.py` — business logic (PDF parsing, DataFrame creation)
  - `webapp/models.py` — data models (`ProcessedFile`, `TransactionMetadata`)
  - `webapp/constants.py` — app constants
  - `webapp/pages/` — Streamlit multipage app (`1_visualizations.py`, `2_about.py`)
- **Desktop**: `tauri/` wraps the PyInstaller binary in a Rust/Tauri WebView
- **Packaging**: `hooks/` contains PyInstaller hooks for all dependencies
- **State management**: Streamlit `st.session_state` for caching parsed results

### Testing Strategy

- **Framework**: `pytest`
- **Pattern**: Function-level tests using `unittest.mock.patch` for Streamlit interactions
- **Fixtures**: Real PDF and CSV files in `tests/fixtures/`
- **Coverage**: End-to-end app flow tests (upload → parse → DataFrame output)
- **Test file**: `tests/test_app.py`

### Git Workflow

- **Branching**: Feature branches, PR-based merging; `development` branch for CI builds
- **Commit style**: Conventional commits with scopes — e.g., `feat:`, `fix:`, `chore(ci):`, `build(deps):`, `docs(README):`
- **Releases**: Tagged (`v*.*.*`) with git-cliff auto-generating changelogs
- **CI/CD**:
  - Build & Release: triggered on tags and `development` branch pushes
  - Docker publish: triggered on tags
  - Healthcheck: hourly cron against `https://statementsensei.streamlit.app/healthz`
  - Stale issues: daily cron to close inactive issues after 60 days

## Agent Working Rules

1. Before writing any code, first describe the solution and wait for user approval. If requirements are unclear, ask clarifying questions before writing any code.
2. If a task requires modifying 3 or more files, stop first and break it down into smaller tasks.
3. After writing code, list out potential issues and suggest corresponding test cases to improve coverage.
4. When finding a bug, first write a test that reproduces the bug, then iterate continuously until the test passes.
5. Every time the user corrects a mistake, add a new rule to this `AGENTS.md` file so the situation does not happen again.
6. For database/repository-level testing, use integration test project. For function-level testing, use unit test project. For user story spec end-to-end tests, use e2e test project. Always check existing test structure and patterns before creating new tests.
7. If a task requires modifying the database (creating/updating stored procedures, schemas, etc.), stop and ask the user to help, then continue.
8. When implementing authentication/session behavior changes, verify the behavior consistently across all pages (not just the login or entry page) and add tests covering multi-page behavior.

## Domain Context

- **Bank statement parsing**: Uses the `monopoly-core` library which handles bank-specific PDF formats, regex extraction, and safety checks
- **Safety check**: Validates that extracted transaction totals balance; warns user if safety check is unavailable for a bank
- **OCR fallback**: If no text layer found in PDF, applies `ocrmypdf` OCR before re-parsing
- **Password handling**: Supports encrypted PDFs via environment variable `PDF_PASSWORDS` (JSON array) or interactive UI input
- **Generic parser**: Falls back to `GenericBank` if the bank is not recognized, with a user-facing warning

## Important Constraints

- No database — this is a stateless PDF processing application
- All PDF processing is client-side (no files stored server-side)
- `PDF_PASSWORDS` environment variable accepts a JSON array string: `'["pass1", "pass2"]'`
- Windows builds are currently disabled due to upstream `pdftotext` build issues
- System dependencies required: `poppler`, `ocrmypdf` (via brew/apt-get)

## External Dependencies

- **monopoly-core**: Core bank statement parsing engine — [GitHub](https://github.com/benjamin-awd/monopoly)
- **Streamlit**: Web UI framework — hosted at `https://statementsensei.streamlit.app/`
- **Tauri**: Desktop app framework — [tauri.app](https://tauri.app)
- **Docker Hub**: Container registry — `benjaminawd/statementsensei`
