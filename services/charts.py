"""
Chart helpers split into two layers:

  Pure helpers  — time-window math, bucket arithmetic, XP scaling/formatting,
                  and aggregation.  No DB access, no FastAPI imports.  Easy to
                  unit-test in isolation.

  Service functions — combine a DB fetch with the pure helpers above and return
                      a ready-to-serialise dict/list.  These are what the route
                      handlers call.
"""

from datetime import datetime, timedelta, timezone

from db import get_conn
from skills import RS3_ORDER

# ---------------------------------------------------------------------------
# XP scaling / formatting
# ---------------------------------------------------------------------------

XP_SCALE_SKILL = 10  # skill XP is stored ×10 in the DB


def scale_skill_xp(value: int | None) -> float:
    return (value or 0) / XP_SCALE_SKILL


def scale_total_xp(value: int | None) -> int:
    return value or 0


def format_skill_xp(value: int | None) -> str:
    scaled = scale_skill_xp(value)
    return f"{scaled:,.1f}".rstrip("0").rstrip(".")


def format_total_xp(value: int | None) -> str:
    return f"{int(scale_total_xp(value)):,}"


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------


def parse_snapshot_ts(ts) -> datetime:
    """Parse a snapshot timestamp to an aware datetime.

    psycopg3 returns TIMESTAMP columns as datetime objects; older code paths
    may still pass plain strings.  Both are handled here.
    """
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def parse_activity_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%d-%b-%Y %H:%M", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Period / timeframe normalisation
# ---------------------------------------------------------------------------


def normalize_bucket(timeframe: str) -> str:
    return {
        "hour": "hour",
        "day": "day",
        "week": "week",
        "month": "month",
        "all": "day",
    }.get(timeframe, "day")


def normalize_period(period: str) -> str:
    return {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
        "all": "all",
    }.get(period, "day")


# ---------------------------------------------------------------------------
# Bucket arithmetic
# ---------------------------------------------------------------------------


def advance_bucket(dt: datetime, bucket: str) -> datetime:
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


def bucket_start(dt: datetime, bucket: str) -> datetime:
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


def build_bucket_starts(start: datetime, end: datetime, bucket: str) -> list[datetime]:
    starts: list[datetime] = []
    current = start
    while current <= end:
        starts.append(current)
        current = advance_bucket(current, bucket)
    return starts


def format_bucket_label(dt: datetime, bucket: str) -> str:
    if bucket == "hour":
        return dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------


def get_period_window(
    period: str, now: datetime, earliest_ts=None
) -> tuple[datetime, datetime, str]:
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

    # "all" — full history, daily buckets
    end = today
    if earliest_ts:
        earliest = parse_snapshot_ts(earliest_ts)
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end
    return start, end, "day"


def get_timeframe_window(
    timeframe: str, now: datetime, earliest_ts=None
) -> tuple[datetime, datetime, str]:
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

    # "all" — full history, daily buckets
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if earliest_ts:
        earliest = parse_snapshot_ts(earliest_ts)
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end
    return start, end, "day"


# ---------------------------------------------------------------------------
# Aggregators (pure)
# ---------------------------------------------------------------------------


def aggregate_bucket_gains(
    rows, bucket: str, starts: list[datetime], value_key: str, scale_fn=scale_total_xp
) -> list[float | int]:
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values: list[float | int] = []
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

        gain_raw = (
            0
            if (bucket_close is None or previous_close is None)
            else max(0, bucket_close - previous_close)
        )
        values.append(scale_fn(gain_raw))
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def aggregate_bucket_totals(
    rows, bucket: str, starts: list[datetime], value_key: str, scale_fn=scale_total_xp
) -> list[float | int]:
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values: list[float | int] = []
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


def aggregate_last_snapshot_totals(
    rows, bucket: str, starts: list[datetime], value_key: str, scale_fn=scale_total_xp
) -> list[float | int | None]:
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values: list[float | int | None] = []
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
        values.append(
            scale_fn(bucket_close if bucket_close is not None else previous_close)
        )
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def build_bucket_gains(rows, bucket: str, value_key: str) -> list[dict]:
    bucket_closing_xp: dict[datetime, int] = {}
    for row in rows:
        ts = parse_snapshot_ts(row["timestamp"])
        b = bucket_start(ts, bucket)
        bucket_closing_xp[b] = row[value_key]

    ordered = sorted(bucket_closing_xp.items(), key=lambda t: t[0])
    points: list[dict] = []
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


# ---------------------------------------------------------------------------
# Misc pure helpers
# ---------------------------------------------------------------------------


def get_window_baseline(cur, cutoff, latest):
    cur.execute(
        "SELECT * FROM snapshots WHERE timestamp <= %s ORDER BY timestamp DESC LIMIT 1",
        (cutoff,),
    )
    baseline = cur.fetchone()
    if baseline:
        return baseline
    cur.execute(
        "SELECT * FROM snapshots WHERE timestamp >= %s ORDER BY timestamp ASC LIMIT 1",
        (cutoff,),
    )
    return cur.fetchone() or latest


def series_has_data(values: list) -> bool:
    return any(value is not None for value in values)


# ---------------------------------------------------------------------------
# Service functions — DB fetch + computation
# Each function is the single source of truth for one API endpoint's data.
# ---------------------------------------------------------------------------


def _fetch_earliest_ts(cur) -> datetime | None:
    cur.execute("SELECT MIN(timestamp) AS min_ts FROM snapshots")
    row = cur.fetchone()
    return row["min_ts"] if row else None


def get_skill_history_data(skill_name: str, timeframe: str) -> list[dict]:
    """Data for /api/skill_history/{skill_name}/{timeframe}."""
    with get_conn() as conn:
        cur = conn.cursor()
        min_ts = _fetch_earliest_ts(cur)
        now = datetime.now(timezone.utc)
        start, end, bucket = get_timeframe_window(timeframe, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)

        cur.execute(
            """
            SELECT s.timestamp, sk.xp
            FROM skills sk
            JOIN snapshots s ON sk.snapshot_id = s.id
            WHERE sk.skill = %s AND s.timestamp < %s
            ORDER BY s.timestamp ASC
            """,
            (skill_name, advance_bucket(end, bucket)),
        )
        rows = cur.fetchall()

    totals = aggregate_bucket_totals(rows, bucket, starts, "xp", scale_skill_xp)
    labels = [format_bucket_label(b, bucket) for b in starts]
    return [{"timestamp": ts, "total": v} for ts, v in zip(labels, totals)]


def get_skills_totals_data(timeframe: str) -> dict:
    """Data for /api/skills_totals/{timeframe}."""
    with get_conn() as conn:
        cur = conn.cursor()
        min_ts = _fetch_earliest_ts(cur)
        now = datetime.now(timezone.utc)
        start, end, bucket = get_timeframe_window(timeframe, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)

        cur.execute(
            """
            SELECT s.timestamp, sk.skill, sk.xp
            FROM skills sk
            JOIN snapshots s ON sk.snapshot_id = s.id
            WHERE s.timestamp < %s
            ORDER BY s.timestamp ASC
            """,
            (advance_bucket(end, bucket),),
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


def get_chart_data(skill_name: str, period: str) -> dict:
    """Data for /api/chart/{skill_name}/{period}."""
    with get_conn() as conn:
        cur = conn.cursor()
        min_ts = _fetch_earliest_ts(cur)
        now = datetime.now(timezone.utc)
        start, end, bucket = get_period_window(period, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)
        end_exclusive = advance_bucket(end, bucket)

        if skill_name.lower() == "total":
            cur.execute(
                """
                SELECT timestamp, total_xp AS xp
                FROM snapshots
                WHERE timestamp < %s
                ORDER BY timestamp ASC
                """,
                (end_exclusive,),
            )
        else:
            cur.execute(
                """
                SELECT s.timestamp, sk.xp
                FROM skills sk
                JOIN snapshots s ON sk.snapshot_id = s.id
                WHERE sk.skill = %s AND s.timestamp < %s
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


def get_total_xp_gains_data(timeframe: str) -> list[dict]:
    """Data for /api/total_xp_gains/{timeframe}."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT timestamp, total_xp FROM snapshots ORDER BY timestamp ASC")
        rows = cur.fetchall()

    return build_bucket_gains(rows, normalize_bucket(timeframe), "total_xp")
