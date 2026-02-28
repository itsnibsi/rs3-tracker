import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from collector import collect_snapshot
from db import get_conn, init_db
from utils import calculate_progress, xp_to_next_level

templates = Jinja2Templates(directory="templates")

RS3_ORDER = [
    "Attack",
    "Constitution",
    "Mining",
    "Strength",
    "Agility",
    "Smithing",
    "Defence",
    "Herblore",
    "Fishing",
    "Ranged",
    "Thieving",
    "Cooking",
    "Prayer",
    "Crafting",
    "Firemaking",
    "Magic",
    "Fletching",
    "Woodcutting",
    "Runecrafting",
    "Slayer",
    "Farming",
    "Construction",
    "Hunter",
    "Summoning",
    "Dungeoneering",
    "Divination",
    "Invention",
    "Archaeology",
    "Necromancy",
]

SKILL_COLORS = {
    "Attack": "#b04d3f",
    "Constitution": "#a43f52",
    "Mining": "#7a6f63",
    "Strength": "#b85d3d",
    "Agility": "#5c8b6d",
    "Smithing": "#7c7063",
    "Defence": "#7f8b97",
    "Herblore": "#4f7f4f",
    "Fishing": "#4f758f",
    "Ranged": "#6b7f52",
    "Thieving": "#6c5a48",
    "Cooking": "#a36a3a",
    "Prayer": "#b9ae8d",
    "Crafting": "#9f7b60",
    "Firemaking": "#b85a32",
    "Magic": "#5e6fb0",
    "Fletching": "#7b6c54",
    "Woodcutting": "#5f7a4f",
    "Runecrafting": "#6e5d9b",
    "Slayer": "#8b4a4a",
    "Farming": "#64834c",
    "Construction": "#8a6b4f",
    "Hunter": "#7a6f54",
    "Summoning": "#8c4f7f",
    "Dungeoneering": "#5e5f67",
    "Divination": "#4e7f89",
    "Invention": "#88724f",
    "Archaeology": "#927154",
    "Necromancy": "#6f5b8f",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(background_loop())
    yield


app = FastAPI(lifespan=lifespan, title="RS3 Tracker")
app.mount("/static", StaticFiles(directory="static"), name="static")


def scale_skill_xp(value):
    return (value or 0) / 10


def scale_total_xp(value):
    return value or 0


def format_skill_xp(value):
    scaled = scale_skill_xp(value)
    return f"{scaled:,.1f}".rstrip("0").rstrip(".")


def format_total_xp(value):
    return f"{int(scale_total_xp(value)):,}"


def parse_snapshot_ts(ts):
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def parse_activity_ts(ts):
    if not ts:
        return None
    for fmt in ("%d-%b-%Y %H:%M", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def normalize_bucket(timeframe):
    buckets = {
        "hour": "hour",
        "day": "day",
        "week": "week",
        "month": "month",
        "all": "day",
    }
    return buckets.get(timeframe, "day")


def normalize_period(period):
    mapping = {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
        "all": "all",
    }
    return mapping.get(period, "day")


def advance_bucket(dt, bucket):
    if bucket == "hour":
        return dt + timedelta(hours=1)
    if bucket == "day":
        return dt + timedelta(days=1)
    if bucket == "week":
        return dt + timedelta(weeks=1)
    if bucket == "month":
        if dt.month == 12:
            return dt.replace(year=dt.year + 1, month=1, day=1)
        return dt.replace(month=dt.month + 1, day=1)
    if bucket == "year":
        return dt.replace(year=dt.year + 1, month=1, day=1)
    return dt + timedelta(days=1)


def build_bucket_starts(start, end, bucket):
    starts = []
    current = start
    while current <= end:
        starts.append(current)
        current = advance_bucket(current, bucket)
    return starts


def get_period_window(period, now, earliest_ts=None):
    p = normalize_period(period)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if p == "day":
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=23)
        return start, end, "hour"

    if p == "week":
        end = today
        start = end - timedelta(days=6)
        return start, end, "day"

    if p == "month":
        end = today
        start = today.replace(day=1)
        return start, end, "day"

    if p == "year":
        end = today
        start = end - timedelta(days=364)
        return start, end, "day"

    # all history daily
    end = today
    if earliest_ts:
        earliest = parse_snapshot_ts(earliest_ts)
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end
    return start, end, "day"


def get_timeframe_window(timeframe, now, earliest_ts=None):
    t = timeframe if timeframe in {"hour", "day", "week", "month", "all"} else "day"

    if t == "hour":
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=23)
        return start, end, "hour"

    if t == "day":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=6)
        return start, end, "day"

    if t == "week":
        end = bucket_start(now, "week")
        start = end - timedelta(weeks=7)
        return start, end, "week"

    if t == "month":
        end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = end.replace(month=1)
        return start, end, "month"

    # all: full history, daily buckets
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if earliest_ts:
        earliest = parse_snapshot_ts(earliest_ts)
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end
    return start, end, "day"


def aggregate_bucket_gains(rows, bucket, starts, value_key, scale_fn=scale_total_xp):
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values = []
    idx = 0
    previous_close = None
    first_start = starts[0]

    while idx < len(parsed) and parsed[idx][0] < first_start:
        previous_close = parsed[idx][1]
        idx += 1

    for b_start in starts:
        b_end = advance_bucket(b_start, bucket)
        bucket_close = previous_close
        while idx < len(parsed) and parsed[idx][0] < b_end:
            bucket_close = parsed[idx][1]
            idx += 1

        if bucket_close is None or previous_close is None:
            gain_raw = 0
        else:
            gain_raw = max(0, bucket_close - previous_close)

        values.append(scale_fn(gain_raw))
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def aggregate_bucket_totals(rows, bucket, starts, value_key, scale_fn=scale_total_xp):
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values = []
    idx = 0
    previous_close = None
    first_start = starts[0]

    while idx < len(parsed) and parsed[idx][0] < first_start:
        previous_close = parsed[idx][1]
        idx += 1

    for b_start in starts:
        b_end = advance_bucket(b_start, bucket)
        bucket_close = previous_close
        while idx < len(parsed) and parsed[idx][0] < b_end:
            bucket_close = parsed[idx][1]
            idx += 1

        values.append(scale_fn(bucket_close or 0))
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def aggregate_last_snapshot_totals(rows, bucket, starts, value_key, scale_fn=scale_total_xp):
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values = []
    idx = 0
    previous_close = None
    first_start = starts[0]
    seen_data = False

    while idx < len(parsed) and parsed[idx][0] < first_start:
        previous_close = parsed[idx][1]
        idx += 1

    for b_start in starts:
        b_end = advance_bucket(b_start, bucket)
        bucket_close = previous_close
        while idx < len(parsed) and parsed[idx][0] < b_end:
            bucket_close = parsed[idx][1]
            idx += 1

        if bucket_close is None and not seen_data:
            values.append(None)
            continue

        seen_data = True
        values.append(scale_fn(bucket_close if bucket_close is not None else previous_close))
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def bucket_start(dt, bucket):
    if bucket == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if bucket == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == "week":
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start - timedelta(days=day_start.weekday())
    if bucket == "month":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if bucket == "year":
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def format_bucket_label(dt, bucket):
    if bucket == "hour":
        return dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"
    return dt.strftime("%Y-%m-%d")


def build_bucket_gains(rows, bucket, value_key):
    bucket_closing_xp = {}

    for row in rows:
        ts = parse_snapshot_ts(row["timestamp"])
        b = bucket_start(ts, bucket)
        bucket_closing_xp[b] = row[value_key]

    ordered = sorted(bucket_closing_xp.items(), key=lambda t: t[0])
    points = []
    prev_xp = None
    for b, closing_xp in ordered:
        gain_raw = 0 if prev_xp is None else max(0, closing_xp - prev_xp)
        points.append(
            {
                "timestamp": b.strftime("%Y-%m-%d %H:%M:%S") + "Z",
                "gain": scale_total_xp(gain_raw),
            }
        )
        prev_xp = closing_xp
    return points


def build_bucket_totals(rows, bucket, value_key):
    bucket_closing_xp = {}

    for row in rows:
        ts = parse_snapshot_ts(row["timestamp"])
        b = bucket_start(ts, bucket)
        bucket_closing_xp[b] = row[value_key]

    ordered = sorted(bucket_closing_xp.items(), key=lambda t: t[0])
    return [
        {
            "timestamp": b.strftime("%Y-%m-%d %H:%M:%S") + "Z",
            "total": scale_total_xp(closing_xp),
        }
        for b, closing_xp in ordered
    ]


def get_window_baseline(cur, cutoff, latest):
    # Prefer snapshot at/before cutoff; if missing, use earliest snapshot in the window.
    cur.execute(
        "SELECT * FROM snapshots WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
        (cutoff,),
    )
    baseline = cur.fetchone()
    if baseline:
        return baseline

    cur.execute(
        "SELECT * FROM snapshots WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT 1",
        (cutoff,),
    )
    return cur.fetchone() or latest


def series_has_data(values):
    return any(value is not None for value in values)


async def background_loop():
    while True:
        try:
            await asyncio.to_thread(collect_snapshot)
        except Exception as e:
            print(f"Collector error: {e}")
        await asyncio.sleep(3600)


def get_dashboard_data():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT s.*, p.username
            FROM snapshots s
            LEFT JOIN players p ON p.id = s.player_id
            ORDER BY s.timestamp DESC
            LIMIT 1
        """
        )
        latest = cur.fetchone()
        if not latest:
            return None

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_today = today_start.strftime("%Y-%m-%d %H:%M:%S")
        prev_today = get_window_baseline(cur, cutoff_today, latest)

        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        prev_24h = get_window_baseline(cur, cutoff_24h, latest)

        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        prev_7d = get_window_baseline(cur, cutoff_7d, latest)

        # Skills & Progress
        cur.execute(
            "SELECT skill, level, xp, rank FROM skills WHERE snapshot_id = ?",
            (latest["id"],),
        )
        current_skills = cur.fetchall()

        prev_skills_map = {}
        if prev_today:
            cur.execute(
                "SELECT skill, xp FROM skills WHERE snapshot_id = ?", (prev_today["id"],)
            )
            for r in cur.fetchall():
                prev_skills_map[r["skill"]] = r["xp"]

        skills_data = []
        level_candidates = []
        for s in current_skills:
            gain = s["xp"] - prev_skills_map.get(s["skill"], s["xp"])
            remaining_xp = xp_to_next_level(s["skill"], s["level"], s["xp"])
            if remaining_xp > 0:
                level_candidates.append(
                    {
                        "skill": s["skill"],
                        "current_level": s["level"],
                        "target_level": s["level"] + 1,
                        "xp_to_next": remaining_xp,
                        "xp_to_next_display": format_skill_xp(remaining_xp),
                    }
                )
            skills_data.append(
                {
                    "skill": s["skill"],
                    "level": s["level"],
                    "xp": s["xp"],
                    "xp_gain": gain,
                    "xp_display": format_skill_xp(s["xp"]),
                    "xp_gain_display": format_skill_xp(gain),
                    "progress": calculate_progress(s["skill"], s["level"], s["xp"]),
                    "color": SKILL_COLORS.get(s["skill"], "#a0a0a0"),
                }
            )

        # Sort by standard RS3 layout order
        order_map = {name: i for i, name in enumerate(RS3_ORDER)}
        skills_data.sort(key=lambda x: order_map.get(x["skill"], 999))
        active_skills = sorted(
            [s for s in skills_data if s["xp_gain"] > 0],
            key=lambda s: s["xp_gain"],
            reverse=True,
        )
        closest_levels = sorted(level_candidates, key=lambda s: s["xp_to_next"])[:3]

        cur.execute("SELECT text, date FROM activities")
        activities = []
        for row in cur.fetchall():
            parsed = parse_activity_ts(row["date"])
            activities.append(
                {
                    "text": row["text"],
                    "date": row["date"],
                    "date_iso": parsed.isoformat().replace("+00:00", "Z") if parsed else None,
                    "sort_ts": parsed or datetime.min.replace(tzinfo=timezone.utc),
                }
            )
        activities.sort(key=lambda a: a["sort_ts"], reverse=True)
        activities = [
            {"text": a["text"], "date": a["date"], "date_iso": a["date_iso"]}
            for a in activities[:20]
        ]

        cur.execute(
            """
            SELECT timestamp, total_xp
            FROM snapshots
            WHERE timestamp >= datetime('now', '-30 days')
            ORDER BY timestamp ASC
        """
        )
        history = cur.fetchall()

        latest_dict = dict(latest)
        latest_dict["total_xp_display"] = format_total_xp(latest["total_xp"])

        xp_24h = latest["total_xp"] - prev_24h["total_xp"]
        xp_7d = latest["total_xp"] - prev_7d["total_xp"]

        return {
            "latest": latest_dict,
            "xp_24h": xp_24h,
            "xp_7d": xp_7d,
            "xp_24h_display": format_total_xp(xp_24h),
            "xp_7d_display": format_total_xp(xp_7d),
            "player_name": latest["username"] or "Unknown Player",
            "top_gainers_today": [
                {"skill": s["skill"], "xp_gain_display": s["xp_gain_display"]}
                for s in active_skills[:5]
            ],
            "closest_levels": closest_levels,
            "skills": skills_data,
            "activities": [dict(a) for a in activities],
            "timestamps": [r["timestamp"] + "Z" for r in history],
            "xp_history": [scale_total_xp(r["total_xp"]) for r in history],
        }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "data": get_dashboard_data()}
    )


@app.get("/api/skill_history/{skill_name}/{timeframe}")
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


@app.get("/api/skills_totals/{timeframe}")
def api_skills_totals(timeframe: str = "day"):
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
        """
            ,
            (end_exclusive,),
        )
        rows = cur.fetchall()

        per_skill_rows = {}
        for row in rows:
            per_skill_rows.setdefault(row["skill"], []).append(row)

        labels = [format_bucket_label(b, bucket) for b in starts]
        order_map = {name: i for i, name in enumerate(RS3_ORDER)}
        series = []
        for skill in sorted(per_skill_rows.keys(), key=lambda x: order_map.get(x, 999)):
            values = aggregate_bucket_totals(
                per_skill_rows[skill], bucket, starts, "xp", scale_skill_xp
            )
            series.append({"skill": skill, "totals": values})

        return {"labels": labels, "series": series}


@app.get("/api/chart/{skill_name}/{period}")
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
                """
                SELECT timestamp, total_xp as xp
                FROM snapshots
                WHERE timestamp < ?
                ORDER BY timestamp ASC
            """,
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

        # Keep the full window labels so the x-axis spans the selected period even if
        # only some buckets contain data.
        has_gains = series_has_data(totals)

        return {
            "labels": labels,
            "totals": totals,
            "has_gains": has_gains,
            "period": normalize_period(period),
            "skill": "Total" if skill_name.lower() == "total" else skill_name,
        }


@app.get("/api/total_xp_gains/{timeframe}")
def api_total_xp_gains(timeframe: str = "day"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT timestamp, total_xp FROM snapshots ORDER BY timestamp ASC")
        rows = cur.fetchall()
        return build_bucket_gains(rows, normalize_bucket(timeframe), "total_xp")


@app.post("/api/update")
def manual_update():
    try:
        collect_snapshot()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
