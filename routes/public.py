"""
Public routes: dashboard page and all read-only API endpoints.

No auth, no admin logic, no SQL.  Each handler does exactly three things:
parse input → call service → return response.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from collector import collect_snapshot
from services.charts import (
    get_chart_data,
    get_skill_history_data,
    get_skills_totals_data,
    get_total_xp_gains_data,
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
    return get_skill_history_data(skill_name, timeframe)


@router.get("/api/skills_totals/{timeframe}")
def api_skills_totals(timeframe: str = "day"):
    return get_skills_totals_data(timeframe)


@router.get("/api/chart/{skill_name}/{period}")
def api_chart(skill_name: str, period: str = "day"):
    return get_chart_data(skill_name, period)


@router.get("/api/total_xp_gains/{timeframe}")
def api_total_xp_gains(timeframe: str = "day"):
    return get_total_xp_gains_data(timeframe)


# ---------------------------------------------------------------------------
# Manual update trigger (intentionally unauthenticated — see REVIEW.md §B.security.1)
# ---------------------------------------------------------------------------


@router.post("/api/update")
async def manual_update():
    try:
        await collect_snapshot()
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
