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

import os
import secrets
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

import psycopg
import psycopg as _psycopg
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from collector import collect_snapshot
from config import ADMIN_PASSWORD, ADMIN_USERNAME
from log import get_logger
from services.admin import get_admin_overview
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
    "httponly": True,
    "samesite": "strict",
    "secure": False,
}


def _get_or_create_csrf_token(request: Request) -> str:
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
# Rendering helper
# ---------------------------------------------------------------------------


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
            "overview": get_admin_overview(),
            "csrf_token": csrf_token,
            "sql": sql,
            "sql_error": sql_error,
            "sql_columns": sql_columns or [],
            "sql_rows": sql_rows or [],
            "sql_rowcount": sql_rowcount,
            "message": message,
        },
    )
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
    # The SQL console by design executes arbitrary SQL — the query itself stays
    # here rather than in a service because there is no fixed query to abstract.
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)

    statement = sql.strip()
    if not statement:
        return _render_admin(
            request, csrf_token=fresh_token, sql=sql, sql_error="SQL query is required."
        )

    without_trailing = statement[:-1].strip() if statement.endswith(";") else statement
    if ";" in without_trailing:
        return _render_admin(
            request,
            csrf_token=fresh_token,
            sql=sql,
            sql_error="Only one SQL statement is allowed per execution.",
        )

    try:
        from db import get_conn

        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(statement)
            keyword = (
                statement.split(maxsplit=1)[0].lower() if statement.split() else ""
            )
            if keyword in {"select", "with"}:
                rows = cur.fetchmany(200)
                columns = [d.name for d in (cur.description or [])]
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
    except psycopg.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql=sql, sql_error=str(exc)
        )


@router.post("/admin/maintenance/update", response_class=HTMLResponse)
async def admin_collect_now(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        await collect_snapshot()
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
        # VACUUM cannot run inside a transaction block in Postgres.
        # Open a dedicated connection with autocommit=True rather than borrowing
        # from the pool — returning a connection with autocommit enabled would
        # leave it in that mode for the next caller.
        database_url = os.environ["DATABASE_URL"]
        with _psycopg.connect(database_url, autocommit=True) as conn:
            conn.execute("VACUUM")
        return _render_admin(
            request, csrf_token=fresh_token, message="VACUUM completed."
        )
    except _psycopg.Error as exc:
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
    # WAL management is handled automatically by Neon — nothing to do here.
    return _render_admin(
        request,
        csrf_token=fresh_token,
        message="WAL checkpointing is managed automatically by Neon.",
    )
