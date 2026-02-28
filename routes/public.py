"""
Public routes: dashboard page and all read-only API endpoints.

No auth, no admin logic.  Heavy lifting is delegated to the services layer.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from collector import collect_snapshot
from db import get_conn
from services.charts import (
    advance_bucket,
    aggregate_bucket_totals,
    aggregate_last_snapshot_totals,
    build_bucket_gains,
    build_bucket_starts,
    format_bucket_label,
    get_period_window,
    get_timeframe_window,
    normalize_bucket,
    normalize_period,
    scale_skill_xp,
    scale_total_xp,
    series_has_data,
)
from services.dashboard import get_dashboard_data
from web import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "data": get_dashboard_data()}
    )


# ---------------------------------------------------------------------------
# Chart / history API
# ---------------------------------------------------------------------------


@router.get("/api/skill_history/{skill_name}/{timeframe}")
def api_skill_history(skill_name: str, timeframe: str = "all"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(timestamp) as min_ts FROM snapshots")
        min_ts_row = cur.fetchone()
        min_ts = min_ts_row["min_ts"] if min_ts_row else None
        now = datetime.now(timezone.utc)
        start, end, bucket = get_timeframe_window(timeframe, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)

        cur.execute(
            """
            SELECT s.timestamp, sk.xp FROM skills sk
            JOIN snapshots s ON sk.snapshot_id = s.id
            WHERE sk.skill = ? AND s.timestamp < ?
            ORDER BY s.timestamp ASC
            """,
            (skill_name, advance_bucket(end, bucket).strftime("%Y-%m-%d %H:%M:%S")),
        )
        rows = cur.fetchall()
        totals = aggregate_bucket_totals(rows, bucket, starts, "xp", scale_skill_xp)
        labels = [format_bucket_label(b, bucket) for b in starts]
        return [{"timestamp": ts, "total": v} for ts, v in zip(labels, totals)]


@router.get("/api/skills_totals/{timeframe}")
def api_skills_totals(timeframe: str = "day"):
    from skills import RS3_ORDER

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(timestamp) as min_ts FROM snapshots")
        min_ts_row = cur.fetchone()
        min_ts = min_ts_row["min_ts"] if min_ts_row else None
        now = datetime.now(timezone.utc)
        start, end, bucket = get_timeframe_window(timeframe, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)
        end_exclusive = advance_bucket(end, bucket).strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            """
            SELECT s.timestamp, sk.skill, sk.xp
            FROM skills sk
            JOIN snapshots s ON sk.snapshot_id = s.id
            WHERE s.timestamp < ?
            ORDER BY s.timestamp ASC
            """,
            (end_exclusive,),
        )
        rows = cur.fetchall()

    per_skill_rows: dict[str, list] = {}
    for row in rows:
        per_skill_rows.setdefault(row["skill"], []).append(row)

    labels = [format_bucket_label(b, bucket) for b in starts]
    order_map = {name: i for i, name in enumerate(RS3_ORDER)}
    series = []
    for skill in sorted(per_skill_rows, key=lambda x: order_map.get(x, 999)):
        values = aggregate_bucket_totals(
            per_skill_rows[skill], bucket, starts, "xp", scale_skill_xp
        )
        series.append({"skill": skill, "totals": values})

    return {"labels": labels, "series": series}


@router.get("/api/chart/{skill_name}/{period}")
def api_chart(skill_name: str, period: str = "day"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(timestamp) as min_ts FROM snapshots")
        min_ts_row = cur.fetchone()
        min_ts = min_ts_row["min_ts"] if min_ts_row else None

        now = datetime.now(timezone.utc)
        start, end, bucket = get_period_window(period, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)
        end_exclusive = advance_bucket(end, bucket).strftime("%Y-%m-%d %H:%M:%S")

        if skill_name.lower() == "total":
            cur.execute(
                "SELECT timestamp, total_xp as xp FROM snapshots WHERE timestamp < ? ORDER BY timestamp ASC",
                (end_exclusive,),
            )
        else:
            cur.execute(
                """
                SELECT s.timestamp, sk.xp as xp
                FROM skills sk
                JOIN snapshots s ON sk.snapshot_id = s.id
                WHERE sk.skill = ? AND s.timestamp < ?
                ORDER BY s.timestamp ASC
                """,
                (skill_name, end_exclusive),
            )

        rows = cur.fetchall()

    scale_fn = scale_total_xp if skill_name.lower() == "total" else scale_skill_xp
    totals = aggregate_last_snapshot_totals(rows, bucket, starts, "xp", scale_fn)
    labels = [format_bucket_label(b, bucket) for b in starts]

    return {
        "labels": labels,
        "totals": totals,
        "has_gains": series_has_data(totals),
        "period": normalize_period(period),
        "skill": "Total" if skill_name.lower() == "total" else skill_name,
    }


@router.get("/api/total_xp_gains/{timeframe}")
def api_total_xp_gains(timeframe: str = "day"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT timestamp, total_xp FROM snapshots ORDER BY timestamp ASC")
        rows = cur.fetchall()
    return build_bucket_gains(rows, normalize_bucket(timeframe), "total_xp")


# ---------------------------------------------------------------------------
# Manual update trigger (intentionally unauthenticated — see REVIEW.md §B.security.1)
# ---------------------------------------------------------------------------


@router.post("/api/update")
async def manual_update():  # Added async
    try:
        await collect_snapshot()  # Added await
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
