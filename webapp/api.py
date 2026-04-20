"""FastAPI backend — serves the Bankclaw dashboard and all API endpoints."""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Load .env — walk up from project root so worktrees find the file too
load_dotenv(Path(__file__).parent.parent / ".env")
if not os.getenv("MONGODB_URL"):
    load_dotenv(find_dotenv())

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from webapp.auth import create_auth_token, verify_auth_token
from webapp.category_definitions import DEFAULT_CATEGORIES, get_effective_categories

# optional MongoDB — gracefully degrade when not configured
try:
    from webapp.repository import (
        archive_custom_category,
        delete_transactions,
        get_transactions_by_date_range,
        save_category_memory,
        save_custom_category,
        save_transactions,
    )
    _MONGO = True
except Exception:  # noqa: BLE001
    _MONGO = False

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Bankclaw API", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=False)


def _current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = verify_auth_token(creds.credentials)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return email


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.post("/api/auth/login")
async def login(request: Request) -> dict:
    body = await request.json()
    email = str(body.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    # password auth against user_repository when available; demo mode otherwise
    password = str(body.get("password", ""))
    if password:
        try:
            from webapp.auth import verify_password  # noqa: PLC0415
            from webapp.user_repository import authenticate_user  # noqa: PLC0415
            record = authenticate_user(email)
            if not record or not verify_password(password, record.get("password_hash", "")):
                raise HTTPException(status_code=401, detail="Invalid credentials")
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            pass  # no MongoDB / user store — demo mode, allow any credentials
    token = create_auth_token(email)
    return {"token": token, "email": email}


@app.get("/api/auth/me")
async def me(user: str = Depends(_current_user)) -> dict:
    return {"email": user}


@app.post("/api/auth/reset-password")
async def reset_password(request: Request) -> dict:
    """Unauthenticated reset — matches Streamlit 'Reset Password' tab behaviour."""
    body = await request.json()
    from webapp.auth import hash_password, normalize_email  # noqa: PLC0415
    email = normalize_email(str(body.get("email", "")))
    new_password = str(body.get("new_password", ""))
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    try:
        from webapp.user_repository import update_password  # noqa: PLC0415
        updated = update_password(email, hash_password(new_password))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="User accounts unavailable") from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"ok": True}


@app.post("/api/auth/change-password")
async def change_password(request: Request, user: str = Depends(_current_user)) -> dict:
    """Authenticated change — requires current password verification."""
    body = await request.json()
    from webapp.auth import hash_password, verify_password  # noqa: PLC0415
    current_password = str(body.get("current_password", ""))
    new_password = str(body.get("new_password", ""))
    if not current_password:
        raise HTTPException(status_code=400, detail="Current password required")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    try:
        from webapp.user_repository import authenticate_user, update_password  # noqa: PLC0415
        record = authenticate_user(user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="User accounts unavailable") from exc
    if not record:
        raise HTTPException(status_code=404, detail="Account not found")
    if not verify_password(current_password, record.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    update_password(user, hash_password(new_password))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
@app.get("/api/transactions")
async def get_transactions(
    start: str | None = None,
    end: str | None = None,
    user: str = Depends(_current_user),
) -> dict:
    if not _MONGO:
        return {"transactions": [], "total": 0}
    from datetime import datetime, timezone  # noqa: PLC0415
    start_date = start or "2000-01-01"
    end_date = end or datetime.now(tz=timezone.utc).date().isoformat()
    try:
        df = get_transactions_by_date_range(start_date, end_date, user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    if df.empty:
        return {"transactions": [], "total": 0}
    records = df.to_dict("records")
    return {"transactions": records, "total": len(records)}


@app.delete("/api/transactions")
async def remove_transactions(request: Request, user: str = Depends(_current_user)) -> dict:
    if not _MONGO:
        return {"deleted": 0}
    body = await request.json()
    df = pd.DataFrame(body.get("transactions", []))
    if df.empty:
        return {"deleted": 0}
    return {"deleted": delete_transactions(df, user)}


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@app.get("/api/categories")
async def get_categories(user: str = Depends(_current_user)) -> dict:
    cats = get_effective_categories(user) if _MONGO else DEFAULT_CATEGORIES
    return {"categories": cats}


@app.post("/api/categories")
async def add_category(request: Request, user: str = Depends(_current_user)) -> dict:
    if not _MONGO:
        raise HTTPException(status_code=503, detail="Database not available")
    body = await request.json()
    save_custom_category(body.get("name", ""), user)
    return {"status": "ok"}


@app.delete("/api/categories/{name}")
async def remove_category(name: str, user: str = Depends(_current_user)) -> dict:
    if not _MONGO:
        raise HTTPException(status_code=503, detail="Database not available")
    archive_custom_category(name, user)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------
@app.post("/api/import")
async def import_statements(
    files: list[UploadFile] = File(...),
    password: str | None = Form(default=None),
    categorize: str = Form(default="true"),
    user: str = Depends(_current_user),
) -> dict:
    from monopoly.pdf import MissingPasswordError, PdfDocument  # noqa: PLC0415
    from webapp.processing import process_pdf  # noqa: PLC0415

    do_categorize = categorize.lower() not in ("false", "0", "no")
    results = []
    all_dfs: list[pd.DataFrame] = []

    for upload in files:
        content = await upload.read()
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            doc = PdfDocument(file_bytes=content)
            doc._name = upload.filename or "upload.pdf"  # noqa: SLF001

            if doc.is_encrypted:
                if password:
                    doc.authenticate(password)
                    if doc.is_encrypted:
                        results.append({"filename": upload.filename, "status": "error", "error": "Wrong password"})
                        continue
                else:
                    results.append({"filename": upload.filename, "status": "error", "error": "Password required"})
                    continue

            result = process_pdf(doc, password=None)
            rows = [
                {
                    "date": str(t.date),
                    "description": t.description,
                    "amount": float(t.amount),
                    "bank": result.file.metadata.bank_name,
                }
                for t in result.file.transactions
            ]
            df = pd.DataFrame(rows)
            all_dfs.append(df)
            results.append({
                "filename": upload.filename,
                "bank": result.file.metadata.bank_name,
                "transaction_count": len(rows),
                "warnings": [{"level": w.level, "message": w.message} for w in result.warnings],
                "status": "ok",
            })
        except Exception as exc:  # noqa: BLE001
            results.append({"filename": upload.filename, "status": "error", "error": str(exc)})
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    if not all_dfs:
        return {"results": results, "transactions": [], "saved": 0}

    combined = pd.concat(all_dfs, ignore_index=True)

    if do_categorize:
        try:
            from webapp.categorizer import categorize_transactions  # noqa: PLC0415
            combined = categorize_transactions(combined, user_email=user)
        except Exception:  # noqa: BLE001
            combined["category"] = "Other"
    else:
        combined["category"] = "Other"

    saved = 0
    if _MONGO:
        try:
            saved = save_transactions(combined, user_email=user)
            save_category_memory(combined, user_email=user, source="auto")
        except Exception:  # noqa: BLE001
            pass  # return extracted transactions even if DB save fails

    return {
        "results": results,
        "transactions": combined.to_dict("records"),
        "saved": saved,
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@app.get("/api/export/csv")
async def export_csv(
    start: str | None = None,
    end: str | None = None,
    user: str = Depends(_current_user),
) -> StreamingResponse:
    if not _MONGO:
        raise HTTPException(status_code=503, detail="Database not available")
    from datetime import datetime, timezone  # noqa: PLC0415
    start_date = start or "2000-01-01"
    end_date = end or datetime.now(tz=timezone.utc).date().isoformat()
    df = get_transactions_by_date_range(start_date, end_date, user)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


# ---------------------------------------------------------------------------
# SPA static file serving (must be last)
# ---------------------------------------------------------------------------
_DASHBOARD = Path(__file__).parent.parent / "dashboard"


@app.get("/")
async def serve_root() -> FileResponse:
    idx = _DASHBOARD / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return JSONResponse({"status": "api-only"})


@app.get("/{path:path}")
async def serve_spa(path: str) -> FileResponse:
    # Serve static assets directly; everything else falls back to index.html
    asset = _DASHBOARD / path
    if asset.exists() and asset.is_file():
        return FileResponse(str(asset))
    idx = _DASHBOARD / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    raise HTTPException(status_code=404)
