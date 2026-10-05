<img src="./docs/logo.svg" width="396" height="91">

Statement Sensei converts bank statement PDFs to CSVs using the [monopoly](https://github.com/benjamin-awd/monopoly) CLI library. The offline version of the app is available on the [releases](https://github.com/benjamin-awd/statementsensei/releases) page.

<h3 align="center">
    🎉 Statement Sensei is now live! 🎉
    <br><br>
    Try it out: <br>
    <a href="https://statementsensei.streamlit.app/">https://statementsensei.streamlit.app/</a>
</h3>

<p align="center">
    <img src="./docs/statement_sensei_demo.gif" width=800>
</p>

# Usage

Statement Sensei can be run as an offline application on Windows, MacOS or Linux.

> ⚠️ Note: Windows does not work currently due to upstream build issues with `pdftotext`.

The offline application runs Streamlit locally, and uses a [WebView](https://tauri.app/v1/references/webview-versions/) window to view the browser frontend at http://localhost:8501.

Supported banks:
| Bank                                   | Credit Statement   | Debit Statement       |
|----------------------------------------|--------------------|-----------------------|
| Bank of America                        | ✅                 | ✅                   |
| Bank of Montreal (BMO)                 | ✅                 | ✅                   |
| Canadian Imperial Bank of Commerce (CIBC) | ✅                 | ✅                   |
| Canadian Tire Bank                     | ✅                 | ❌                   |
| Capital One Canada                     | ✅                 | ❌                   |
| Chase                                  | ✅                 | ❌                   |
| Citibank                               | ✅                 | ❌                   |
| DBS/POSB                               | ✅                 | ✅                   |
| HSBC                                   | ✅                 | ❌                   |
| Maybank                                | ✅                 | ✅                   |
| OCBC                                   | ✅                 | ✅                   |
| Royal Bank of Canada (RBC)             | ✅                 | ✅                   |
| Schwab Bank                            | N/A                | ✅                   |
| Scotiabank                             | ✅                 | ✅                   |
| Standard Chartered                     | ✅                 | ❌                   |
| TD Canada Trust                        | ✅                 | ✅                   |
| Trust                                  | ✅                 | ❌                   |
| UOB                                    | ✅                 | ✅                   |
| US Bank                                | ✅                 | ❌                   |
| Zürcher Kantonalbank                   | ❌                 | ✅                   |

# Installation

> [!WARNING]
> The offline app may raise security warnings during installation.

Specifically on MacOS, the application will show an "app is damaged and can't be opened" error.

These security warnings happen because the release binaries are unsigned, and are incorrectly flagged as malware.

To get around this, follow these steps for [MacOS](https://support.apple.com/en-sg/guide/mac-help/mh40616/mac) / [Windows](https://stackoverflow.com/questions/54733909/windows-defender-alert-users-from-my-pyinstaller-exe).

The Windows Defender alert can be bypassed by clicking "More info" -> "Run anyway".

# Development
Install system dependencies using brew or apt-get (necessary since `pdftotext` needs them)

```sh
apt-get install build-essential libpoppler-cpp-dev pkg-config ocrmypdf
```

or

```sh
brew install gcc@11 pkg-config poppler ocrmypdf
```

Install app dependencies with uv:
```shell
uv venv
source .venv/bin/activate
uv pip install -e .
```

To run the consumer-facing application:
```shell
python entrypoint.py
```

To run the application in developer mode:
```shell
streamlit run webapp/app.py
```

## Docker
Otherwise, to run the application as a container:
```sh
docker compose up
```

or:

```sh
docker pull benjaminawd/statementsensei:latest
docker run -p 8501:8501 benjaminawd/statementsensei:latest
```

If running locally with docker: you can either store passwords in an environment variable as a string

```sh
export PDF_PASSWORDS='["pass123", "otherpw123"]'
```

or store them in an .env file in the project root:

```sh
echo 'PDF_PASSWORDS=["foo"]' > .env
```

## Jev Category Detection + MongoDB

Automatic category detection uses [Jev by TypeSafe](https://typesafe.ai). Configure the API key on the machine or server running Bankclaw. MongoDB stores transactions and remembered category corrections.

| Variable | Required | Description |
|---|---|---|
| `TYPESAFE_API_KEY` | For AI categories | TypeSafe API key for Jev category detection — see [typesafe.ai](https://typesafe.ai) |
| `TYPESAFE_DEFAULT_MODEL` | No | Jev model name (default: `jev-latest`) |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key for AI Coach and goal suggestions |
| `DEEPSEEK_MODEL` | No | Coach/advisor model name (default: `deepseek-v4-pro`) |
| `MONGODB_URL` | For storage | MongoDB Atlas connection string (e.g. `mongodb+srv://user:***@cluster.mongodb.net/`) |
| `MONGODB_DB_NAME` | No | Database name (default: `bankclaw`) |

```sh
export TYPESAFE_API_KEY="***"
export TYPESAFE_DEFAULT_MODEL="jev-latest"  # optional
export MONGODB_URL="mongodb+srv://user:***@cluster.mongodb.net/"
export MONGODB_DB_NAME="bankclaw"  # optional
```

For local development, add these variables to your existing `.env` file, using `.env.example` as a reference. Keep API keys out of Git. For hosted deployments, set them in your hosting provider's environment variables and restart the app.

The dashboard categorises transactions automatically during PDF import. Saved category matches take priority; unmatched descriptions are sent to Jev in batches with one typed `Choice` question per transaction. The choices use the caller's allowed categories, including `Other`. Missing or invalid category answers become `Other`, and transaction order is preserved.

If Jev is unavailable or its key is missing, dashboard imports still return the extracted transactions with `Other` categories. Review the results before relying on them. In Streamlit, use **Generate AI Categories**, review and edit the suggestions, then save to MongoDB. The **3 History** page lets you browse saved transactions.

AI Coach and goal suggestions use DeepSeek separately. Set `DEEPSEEK_API_KEY` to enable those features; it is not used for category detection.

## Development

### Running the Development Server

```bash
# Quick start (kills existing processes and starts fresh)
./start.sh

# Or start the dashboard manually with uv
uv sync
uv run uvicorn webapp.api:app --host 127.0.0.1 --port 8501

# For the Streamlit interface instead
uv run streamlit run webapp/app.py
```

The app will be available at **http://localhost:8501**

### Environment Setup

Create or update `.env` in the project root with the variables described in **Jev Category Detection + MongoDB** above.

### Parser updates and validation

Bankclaw uses `monopoly-core==0.23.1`, including upstream parsing improvements and support for Schwab and US Bank.
Dependabot checks for parser updates daily. After updating the parser, regenerate the committed deployment files:

```bash
uv lock
uv sync --group dev
uv build --sdist
.github/hooks/include_webapp_in_requirements.sh
uv run python .github/scripts/check_release_artifacts.py
```

CI rejects stale source packages, dependency exports, and packages containing `.env` files.
Run the isolated browser import test locally with:

```bash
uv sync --group dev --group browser
uv run --group browser playwright install chromium
BANKCLAW_RUN_BROWSER_TESTS=1 uv run --group browser pytest tests/e2e/test_dashboard_import_browser.py -q
```

The browser test signs in, imports the example PDF, verifies Jev categories, and opens the ledger.
It uses a synthetic account and mocked Jev responses with database access disabled.
See [deployment monitoring](DEPLOY.md#dashboard-monitoring) to enable checks against your deployed dashboard.

# Features
- Supports uploading multiple bank statements
- Allows unlocking of PDFs using user-provided credentials via the frontend
- AI-powered transaction categorisation via Jev using typed category choices (optional)
- MongoDB Atlas storage with duplicate-safe upserts (optional)
- Transaction history page with date-range filtering and CSV export
