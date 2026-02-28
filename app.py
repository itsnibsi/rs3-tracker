import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from collector import collect_snapshot
from db import get_conn, init_db

templates = Jinja2Templates(directory="templates")


def get_latest_snapshot():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row


def get_snapshot_older_than(hours):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM snapshots
        WHERE timestamp <= datetime('now', ?)
        ORDER BY timestamp DESC
        LIMIT 1
    """,
        (f"-{hours} hours",),
    )
    row = cur.fetchone()
    conn.close()
    return row


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(background_loop())
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


async def background_loop():
    while True:
        try:
            collect_snapshot()
        except Exception as e:
            print("Collector error:", e)
        await asyncio.sleep(3600 - (time.time() % 3600))


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT timestamp, total_xp FROM snapshots ORDER BY timestamp")
    rows = cur.fetchall()

    timestamps = [r["timestamp"] for r in rows]
    xp = [r["total_xp"] for r in rows]

    latest = get_latest_snapshot()
    day_old = get_snapshot_older_than(24)
    week_old = get_snapshot_older_than(168)

    xp_24h = 0
    xp_7d = 0

    if latest and day_old:
        xp_24h = latest["total_xp"] - day_old["total_xp"]

    if latest and week_old:
        xp_7d = latest["total_xp"] - week_old["total_xp"]

    conn.close()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "timestamps": timestamps,
            "xp": xp,
            "xp_24h": xp_24h,
            "xp_7d": xp_7d,
        },
    )


@app.get("/skills", response_class=HTMLResponse)
def skills(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    latest = get_latest_snapshot()
    day_old = get_snapshot_older_than(24)

    cur.execute(
        """
        SELECT skill, level, xp, rank
        FROM skills
        WHERE snapshot_id = ?
        ORDER BY level DESC
    """,
        (latest["id"],),
    )

    current_skills = cur.fetchall()

    deltas = {}
    if day_old:
        cur.execute(
            """
            SELECT skill, xp
            FROM skills
            WHERE snapshot_id = ?
        """,
            (day_old["id"],),
        )
        for row in cur.fetchall():
            deltas[row["skill"]] = row["xp"]

    skill_data = []
    for s in current_skills:
        xp_gain = 0
        if s["skill"] in deltas:
            xp_gain = s["xp"] - deltas[s["skill"]]
        skill_data.append(
            {
                "skill": s["skill"],
                "level": s["level"],
                "xp": s["xp"],
                "rank": s["rank"],
                "xp_gain": xp_gain,
            }
        )

    conn.close()

    return templates.TemplateResponse(
        "skills.html", {"request": request, "skills": skill_data}
    )


@app.get("/update")
def manual_update():
    try:
        collect_snapshot()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
