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


def get_total_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 1")
    latest = cur.fetchone()
    conn.close()
    if not latest:
        return {}
    return {
        "total_xp": latest["total_xp"],
        "total_level": latest["total_level"],
        "combat_level": latest["combat_level"],
        "overall_rank": latest["overall_rank"],
        "quest_points": latest["quest_points"],
    }


def get_biggest_gain(period_hours=24):
    conn = get_conn()
    cur = conn.cursor()
    end = datetime.utcnow()
    start = end - timedelta(hours=period_hours)
    cur.execute(
        """
        SELECT s.timestamp, s.total_xp
        FROM snapshots s
        WHERE s.timestamp BETWEEN ? AND ?
        ORDER BY s.timestamp ASC
    """,
        (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
    )
    rows = cur.fetchall()
    conn.close()
    if len(rows) < 2:
        return 0
    return rows[-1]["total_xp"] - rows[0]["total_xp"]


def get_xp_streak():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT timestamp, total_xp FROM snapshots ORDER BY timestamp ASC")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return 0
    streak = 0
    prev_xp = None
    for r in reversed(rows):
        if prev_xp is None:
            prev_xp = r["total_xp"]
            streak += 1
        else:
            if r["total_xp"] < prev_xp:
                break
            streak += 1
            prev_xp = r["total_xp"]
    return streak


def get_previous_snapshot(hours=24):
    conn = get_conn()
    cur = conn.cursor()

    # Compute cutoff
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    # Snapshots before cutoff
    cur.execute(
        """
        SELECT * FROM snapshots
        WHERE timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 1
    """,
        (cutoff_str,),
    )
    snapshot = cur.fetchone()

    if snapshot:
        conn.close()
        return snapshot

    # fallback: earliest snapshot
    cur.execute("""
        SELECT * FROM snapshots
        ORDER BY timestamp ASC
        LIMIT 1
    """)
    snapshot = cur.fetchone()
    conn.close()
    return snapshot


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

    total_stats = get_total_stats()
    xp_24h = get_biggest_gain(24)
    xp_7d = get_biggest_gain(168)
    streak_days = get_xp_streak()

    # Fetch current skills with progress bars
    latest = get_latest_snapshot()
    prev = get_previous_snapshot(24)
    skill_list = []
    if latest:
        cur.execute(
            "SELECT skill, level, xp, rank FROM skills WHERE snapshot_id = ?",
            (latest["id"],),
        )
        current_skills = cur.fetchall()
        prev_map = {}
        if prev:
            cur.execute(
                "SELECT skill, xp FROM skills WHERE snapshot_id = ?", (prev["id"],)
            )
            for r in cur.fetchall():
                prev_map[r["skill"]] = r["xp"]
        for s in current_skills:
            gain = s["xp"] - prev_map.get(s["skill"], s["xp"])
            # Simple XP to next level progress
            # RS3 formula approximation: next_level_xp = 0.25 * level^3 + something...
            next_level_xp = int((s["level"] + 1) ** 3 * 1000)  # simple approximation
            progress = min(max((s["xp"] % next_level_xp) / next_level_xp, 0), 1)
            skill_list.append(
                {
                    "skill": s["skill"],
                    "level": s["level"],
                    "xp": s["xp"],
                    "rank": s["rank"],
                    "xp_gain": gain,
                    "progress": progress,
                }
            )

    # Fetch latest activities
    cur.execute("""
        SELECT text, date FROM activities
        ORDER BY id DESC
        LIMIT 20
    """)
    activities = cur.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "timestamps": timestamps,
            "xp": xp,
            "total_stats": total_stats,
            "xp_24h": xp_24h,
            "xp_7d": xp_7d,
            "streak_days": streak_days,
            "skills": skill_list,
            "activities": activities,
        },
    )


@app.get("/skills", response_class=HTMLResponse)
def skills(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    latest = get_latest_snapshot()
    prev = get_previous_snapshot(24)  # fixed delta

    # Get current skills
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

    # Map previous XP
    prev_xp_map = {}
    if prev:
        cur.execute(
            """
            SELECT skill, xp
            FROM skills
            WHERE snapshot_id = ?
        """,
            (prev["id"],),
        )
        for row in cur.fetchall():
            prev_xp_map[row["skill"]] = row["xp"]

    skill_data = []
    for s in current_skills:
        delta = s["xp"] - prev_xp_map.get(s["skill"], s["xp"])
        skill_data.append(
            {
                "skill": s["skill"],
                "level": s["level"],
                "xp": s["xp"],
                "rank": s["rank"],
                "xp_gain": delta,
            }
        )

    conn.close()
    return templates.TemplateResponse(
        "skills.html", {"request": request, "skills": skill_data}
    )


@app.get("/skill_history/{skill_name}")
def skill_history(skill_name: str, timeframe: str = "all"):
    conn = get_conn()
    cur = conn.cursor()

    # Determine start datetime based on timeframe
    now = datetime.utcnow()
    if timeframe == "hour":
        start = now - timedelta(hours=1)
    elif timeframe == "day":
        start = now - timedelta(days=1)
    elif timeframe == "week":
        start = now - timedelta(weeks=1)
    elif timeframe == "month":
        start = now - timedelta(days=30)
    elif timeframe == "year":
        start = now - timedelta(days=365)
    else:
        start = datetime(1970, 1, 1)

    cur.execute(
        """
        SELECT s.timestamp, sk.xp
        FROM skills sk
        JOIN snapshots s ON sk.snapshot_id = s.id
        WHERE sk.skill = ? AND s.timestamp >= ?
        ORDER BY s.timestamp ASC
    """,
        (skill_name, start.strftime("%Y-%m-%d %H:%M:%S")),
    )

    data = [{"timestamp": row["timestamp"], "xp": row["xp"]} for row in cur.fetchall()]
    conn.close()
    return data


@app.get("/skill/{skill_name}", response_class=HTMLResponse)
def skill_detail(request: Request, skill_name: str, timeframe: str = "all"):
    conn = get_conn()
    cur = conn.cursor()

    # Determine start datetime based on timeframe
    now = datetime.utcnow()
    if timeframe == "hour":
        start = now - timedelta(hours=1)
    elif timeframe == "day":
        start = now - timedelta(days=1)
    elif timeframe == "week":
        start = now - timedelta(weeks=1)
    elif timeframe == "month":
        start = now - timedelta(days=30)
    elif timeframe == "year":
        start = now - timedelta(days=365)
    else:
        start = datetime(1970, 1, 1)

    cur.execute(
        """
        SELECT s.timestamp, sk.xp
        FROM skills sk
        JOIN snapshots s ON sk.snapshot_id = s.id
        WHERE sk.skill = ? AND s.timestamp >= ?
        ORDER BY s.timestamp ASC
    """,
        (skill_name, start.strftime("%Y-%m-%d %H:%M:%S")),
    )
    data = cur.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "skill_detail.html",
        {"request": request, "skill": skill_name, "data": data, "timeframe": timeframe},
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
