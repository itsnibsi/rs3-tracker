"""
Admin routes — protected by HTTP Basic auth, CSRF tokens, and per-IP rate limiting.

Security model
--------------
* HTTP Basic credentials must match ADMIN_USERNAME / ADMIN_PASSWORD env vars.
* Every admin POST form must include a ``csrf_token`` hidden field whose value
  matches the ``csrf_token`` cookie set on the last admin GET.  This is the
  double-submit cookie pattern — no server-side session state required.
* Admin endpoints (GET and POST) are rate-limited to ADMIN_RATE_LIMIT requests
  per IP per minute.  The limit is intentionally generous enough to never
  affect legitimate use but blocks unsophisticated brute-force attempts.
"""

import secrets
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from collector import collect_snapshot
from config import ADMIN_PASSWORD, ADMIN_USERNAME, DB_PATH
from db import get_conn
from log import get_logger
from web import templates

logger = get_logger(__name__)

router = APIRouter()
_security = HTTPBasic()

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

_rate_lock = threading.Lock()
_ip_log: dict[str, list[datetime]] = defaultdict(list)

ADMIN_RATE_LIMIT = 60  # max requests per window per IP
ADMIN_RATE_WINDOW = timedelta(minutes=1)


def _client_ip(request: Request) -> str:
    """Return the real client IP, accounting for Cloud Run's X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    window_start = now - ADMIN_RATE_WINDOW
    with _rate_lock:
        _ip_log[ip] = [t for t in _ip_log[ip] if t > window_start]
        if len(_ip_log[ip]) >= ADMIN_RATE_LIMIT:
            logger.warning("Admin rate limit hit for IP %s", ip)
            raise HTTPException(
                status_code=429,
                detail="Too many requests — please wait a moment before trying again.",
            )
        _ip_log[ip].append(now)


# ---------------------------------------------------------------------------
# CSRF helpers  (double-submit cookie pattern)
# ---------------------------------------------------------------------------

_CSRF_COOKIE = "csrf_token"
_CSRF_FIELD = "csrf_token"
_CSRF_COOKIE_OPTS: dict = {
    "httponly": True,  # JS cannot read it; server injects value into forms
    "samesite": "strict",
    "secure": False,  # set True if the app is served exclusively over HTTPS
}


def _get_or_create_csrf_token(request: Request) -> str:
    """Return the CSRF token from the cookie, generating a fresh one if absent."""
    return request.cookies.get(_CSRF_COOKIE) or secrets.token_hex(32)


def _verify_csrf(request: Request, form_token: str) -> None:
    cookie_token = request.cookies.get(_CSRF_COOKIE, "")
    if not cookie_token or not secrets.compare_digest(cookie_token, form_token):
        logger.warning("CSRF check failed for IP %s", _client_ip(request))
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


# ---------------------------------------------------------------------------
# HTTP Basic auth dependency
# ---------------------------------------------------------------------------


def require_admin(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> HTTPBasicCredentials:
    _enforce_rate_limit(request)

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Admin credentials are not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD.",
        )

    user_ok = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


def _get_admin_overview() -> dict:
    table_counts = []
    with get_conn() as conn:
        cur = conn.cursor()
        for table in ("players", "snapshots", "skills", "activities"):
            cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
            row = cur.fetchone()
            table_counts.append({"name": table, "count": row["count"]})

        cur.execute("SELECT timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 1")
        latest_row = cur.fetchone()

    db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "db_path": str(DB_PATH),
        "db_size_bytes": db_size_bytes,
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        "latest_snapshot_ts": latest_row["timestamp"] if latest_row else None,
        "table_counts": table_counts,
    }


def _render_admin(
    request: Request,
    *,
    csrf_token: str,
    sql: str = "",
    sql_error: str | None = None,
    sql_columns: list | None = None,
    sql_rows: list | None = None,
    sql_rowcount: int | None = None,
    message: str | None = None,
) -> HTMLResponse:
    response = templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "overview": _get_admin_overview(),
            "csrf_token": csrf_token,
            "sql": sql,
            "sql_error": sql_error,
            "sql_columns": sql_columns or [],
            "sql_rows": sql_rows or [],
            "sql_rowcount": sql_rowcount,
            "message": message,
        },
    )
    # Refresh the CSRF cookie on every admin response so it doesn't expire mid-session.
    response.set_cookie(_CSRF_COOKIE, csrf_token, **_CSRF_COOKIE_OPTS)
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
):
    csrf_token = _get_or_create_csrf_token(request)
    return _render_admin(request, csrf_token=csrf_token)


@router.post("/admin/sql", response_class=HTMLResponse)
def admin_run_sql(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    sql: str = Form(...),
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)

    statement = sql.strip()
    if not statement:
        return _render_admin(
            request, csrf_token=fresh_token, sql=sql, sql_error="SQL query is required."
        )

    # Reject multi-statement input.
    without_trailing = statement[:-1].strip() if statement.endswith(";") else statement
    if ";" in without_trailing:
        return _render_admin(
            request,
            csrf_token=fresh_token,
            sql=sql,
            sql_error="Only one SQL statement is allowed per execution.",
        )

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(statement)
            keyword = (
                statement.split(maxsplit=1)[0].lower() if statement.split() else ""
            )
            if keyword in {"select", "pragma", "with"}:
                rows = cur.fetchmany(200)
                columns = [d[0] for d in (cur.description or [])]
                return _render_admin(
                    request,
                    csrf_token=fresh_token,
                    sql=sql,
                    sql_columns=columns,
                    sql_rows=[dict(row) for row in rows],
                    message=f"Query succeeded. Showing up to 200 rows ({len(rows)} returned).",
                )
            conn.commit()
            return _render_admin(
                request,
                csrf_token=fresh_token,
                sql=sql,
                sql_rowcount=cur.rowcount,
                message=f"Statement succeeded. Rows affected: {cur.rowcount}.",
            )
    except sqlite3.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql=sql, sql_error=str(exc)
        )


@router.post("/admin/maintenance/update", response_class=HTMLResponse)
async def admin_collect_now(  # Added async
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        await collect_snapshot()  # Added await
        return _render_admin(
            request, csrf_token=fresh_token, message="Snapshot collected successfully."
        )
    except Exception as exc:
        return _render_admin(
            request,
            csrf_token=fresh_token,
            sql_error=f"Snapshot collection failed: {exc}",
        )


@router.post("/admin/maintenance/vacuum", response_class=HTMLResponse)
def admin_vacuum(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        with get_conn() as conn:
            conn.execute("VACUUM")
        return _render_admin(
            request, csrf_token=fresh_token, message="VACUUM completed."
        )
    except sqlite3.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql_error=f"VACUUM failed: {exc}"
        )


@router.post("/admin/maintenance/checkpoint", response_class=HTMLResponse)
def admin_checkpoint(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        with get_conn() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
        return _render_admin(
            request, csrf_token=fresh_token, message="WAL checkpoint completed."
        )
    except sqlite3.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql_error=f"WAL checkpoint failed: {exc}"
        )
