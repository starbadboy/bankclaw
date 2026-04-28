# Deploying Bankclaw to Railway

Railway builds from the [`Dockerfile`](./Dockerfile) and runs the FastAPI server which serves both the API and the React dashboard.

## 1. One-time setup

1. Create a Railway account at <https://railway.app>
2. Install the CLI (optional, but handy):
   ```bash
   brew install railwayapp/railway/railway
   railway login
   ```

## 2. Create the project

**Option A — From the dashboard (easiest):**
- New Project → Deploy from GitHub repo → pick this repo
- Railway auto-detects `Dockerfile` and `railway.json`

**Option B — From the CLI:**
```bash
railway init
railway link          # link to an existing project if you already created one
railway up            # first deploy
```

## 3. Set environment variables

In **Project → Variables**, add:

| Variable | Required | Notes |
|---|---|---|
| `MONGODB_URL` | yes (for persistence) | `mongodb+srv://...` — use Atlas or Railway's MongoDB plugin |
| `MONGODB_DB_NAME` | no | defaults to `bankclaw` |
| `DEEPSEEK_API_KEY` | optional | enables AI categorisation |
| `DEEPSEEK_MODEL` | optional | defaults to `deepseek-v4-pro`; use `deepseek-v4-flash` for lower-cost non-thinking mode |
| `OPENAI_API_KEY` | optional | alternative AI provider |
| `PDF_PASSWORDS` | optional | JSON array, e.g. `["pass1","pass2"]` |
| `AUTH_SECRET` | recommended | HMAC key for session tokens (any long random string) |
| `PORT` | auto | injected by Railway — do not set manually |

> `railway variables set MONGODB_URL=...` works from the CLI too.

## 4. MongoDB

Two choices:

- **MongoDB Atlas (recommended)** — free tier, better backups. Paste the SRV URI into `MONGODB_URL`.
- **Railway MongoDB plugin** — New → Database → MongoDB. Railway auto-injects `MONGO_URL`; rename to `MONGODB_URL` via a reference variable or update `webapp/db.py` to check both.

## 5. Domain

After the first successful deploy:
- **Settings → Networking → Generate Domain** for a free `*.up.railway.app` URL
- Or attach a custom domain and add the CNAME record they show you

## 6. Verify

```bash
curl https://<your-app>.up.railway.app/api/health
# → {"status":"ok","mongo":"enabled"}
```

Open the root URL in a browser — the React dashboard should load.

## Troubleshooting

- **Build OOM** — bump builder resources in Settings, or trim `--all-extras` in the Dockerfile if OCR isn't needed.
- **`pdftotext` import error** — confirm `libpoppler-cpp-dev` is in the Dockerfile apt list (it is, by default).
- **PDFs time out** — Railway has no hard request limit, but large OCR jobs may hit memory caps on the $5 plan. Upgrade plan or set `ocrmypdf` flags to reduce memory.
- **Logs**: `railway logs` or use the dashboard's live log stream.

## Local parity check

Before pushing, verify the container builds and runs locally:

```bash
docker build -t bankclaw .
docker run --rm -p 8501:8501 --env-file .env bankclaw
open http://localhost:8501
```
