"""
Dashboard assembly service.

Pulls data from the DB and returns a plain dict ready for the template.
No FastAPI / HTTP concerns here.
"""

import re
from datetime import datetime, timedelta, timezone

from db import get_conn
from services.charts import (
    format_skill_xp,
    format_total_xp,
    get_window_baseline,
    parse_activity_ts,
    scale_total_xp,
)
from skills import ACTIVITY_TYPE_META, RS3_ORDER, SKILL_COLORS
from utils import calculate_progress, xp_to_next_level

# ---------------------------------------------------------------------------
# Activity helpers
# ---------------------------------------------------------------------------


def detect_activity_skill(text: str | None) -> str | None:
    lowered = (text or "").lower()
    for skill in RS3_ORDER:
        if re.search(rf"\b{re.escape(skill.lower())}\b", lowered):
            return skill
    return None


def classify_activity_meta(text: str | None, details: str | None = None) -> dict:
    combined = " ".join(part for part in (details, text) if part)
    lowered = combined.lower()

    type_key = "activity"
    if "quest" in lowered:
        type_key = "quest"
    elif "clue" in lowered or "treasure trail" in lowered:
        type_key = "clue"
    elif "levelled" in lowered or "leveled" in lowered or "advanced" in lowered:
        type_key = "level"
    elif "killed" in lowered or "defeated" in lowered or "slain" in lowered:
        type_key = "kill"
    elif "drop" in lowered or "received" in lowered or "found" in lowered:
        type_key = "loot"
    elif "achievement" in lowered or "completed" in lowered:
        type_key = "achievement"
    elif "unlocked" in lowered:
        type_key = "unlock"

    skill = detect_activity_skill(combined) if type_key == "level" else None
    fallback = ACTIVITY_TYPE_META["activity"]
    meta = ACTIVITY_TYPE_META.get(type_key, fallback)
    color = SKILL_COLORS.get(skill, meta["color"]) if skill else meta["color"]
    return {
        "type_key": type_key,
        "type_label": meta["label"],
        "skill": skill,
        "color": color,
    }


# ---------------------------------------------------------------------------
# Main dashboard query
# ---------------------------------------------------------------------------


def _ts_to_str(ts) -> str | None:
    """Normalise a timestamp column value to an ISO string for the template."""
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)


def get_dashboard_data() -> dict | None:
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

        cutoff_24h = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        prev_24h = get_window_baseline(cur, cutoff_24h, latest)

        cutoff_7d = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        prev_7d = get_window_baseline(cur, cutoff_7d, latest)

        # ------------------------------------------------------------------
        # Skills
        # ------------------------------------------------------------------
        cur.execute(
            "SELECT skill, level, xp, rank FROM skills WHERE snapshot_id = %s",
            (latest["id"],),
        )
        current_skills = cur.fetchall()

        prev_skills_map: dict[str, int] = {}
        prev_levels_map: dict[str, int] = {}
        if prev_today:
            cur.execute(
                "SELECT skill, xp, level FROM skills WHERE snapshot_id = %s",
                (prev_today["id"],),
            )
            for r in cur.fetchall():
                prev_skills_map[r["skill"]] = r["xp"]
                prev_levels_map[r["skill"]] = r["level"]

        skills_data: list[dict] = []
        level_candidates: list[dict] = []
        levels_gained_today = 0

        for s in current_skills:
            gain = s["xp"] - prev_skills_map.get(s["skill"], s["xp"])
            prev_level = prev_levels_map.get(s["skill"], s["level"])
            levels_gained_today += max(0, s["level"] - prev_level)
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

        order_map = {name: i for i, name in enumerate(RS3_ORDER)}
        skills_data.sort(key=lambda x: order_map.get(x["skill"], 999))
        active_skills = sorted(
            [s for s in skills_data if s["xp_gain"] > 0],
            key=lambda s: s["xp_gain"],
            reverse=True,
        )
        closest_levels = sorted(level_candidates, key=lambda s: s["xp_to_next"])[:3]

        # ------------------------------------------------------------------
        # Activities
        # ------------------------------------------------------------------
        cur.execute("SELECT id, text, date, details FROM activities")
        activities: list[dict] = []
        for row in cur.fetchall():
            parsed = parse_activity_ts(row["date"])
            meta = classify_activity_meta(row["text"], row["details"])
            activities.append(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "date": row["date"],
                    "details": row["details"],
                    "date_iso": parsed.isoformat().replace("+00:00", "Z")
                    if parsed
                    else None,
                    "sort_ts": parsed or datetime.min.replace(tzinfo=timezone.utc),
                    **meta,
                }
            )
        activities.sort(key=lambda a: (a["sort_ts"], a["id"]), reverse=True)

        today_quests_finished = sum(
            1
            for a in activities
            if a["type_key"] == "quest" and a["sort_ts"] >= today_start
        )

        activities_out = [
            {k: v for k, v in a.items() if k != "sort_ts"} for a in activities
        ]

        # ------------------------------------------------------------------
        # 30-day XP history (sidebar chart)
        # psycopg returns datetime objects for TIMESTAMP columns, so we
        # normalise to ISO strings here rather than concatenating "+ Z".
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT timestamp, total_xp
            FROM snapshots
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            ORDER BY timestamp ASC
            """
        )
        history = cur.fetchall()

        # ------------------------------------------------------------------
        # Derived stats
        # ------------------------------------------------------------------
        latest_dict = dict(latest)
        latest_dict["total_xp_display"] = format_total_xp(latest["total_xp"])
        # Normalise timestamp to string so the template can render it safely.
        latest_dict["timestamp"] = _ts_to_str(latest_dict.get("timestamp"))

        xp_today = max(0, latest["total_xp"] - prev_today["total_xp"])
        rank_delta = prev_today["overall_rank"] - latest["overall_rank"]
        if rank_delta > 0:
            rank_delta_display = f"+{rank_delta:,}"
            rank_delta_class = "xp-gain-positive"
        elif rank_delta < 0:
            rank_delta_display = f"-{abs(rank_delta):,}"
            rank_delta_class = "xp-gain-negative"
        else:
            rank_delta_display = "0"
            rank_delta_class = ""

        xp_24h = latest["total_xp"] - prev_24h["total_xp"]
        xp_7d = latest["total_xp"] - prev_7d["total_xp"]

        return {
            "latest": latest_dict,
            "today_highlights": {
                "xp_today": xp_today,
                "xp_today_display": format_total_xp(xp_today),
                "levels_gained_today": levels_gained_today,
                "quests_finished_today": today_quests_finished,
                "rank_delta_today": rank_delta,
                "rank_delta_today_display": rank_delta_display,
                "rank_delta_today_class": rank_delta_class,
            },
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
            "activities": activities_out,
            # Timestamps normalised to ISO strings with Z suffix for Chart.js
            "timestamps": [
                (_ts_to_str(r["timestamp"]) or "").rstrip("Z") + "Z" for r in history
            ],
            "xp_history": [scale_total_xp(r["total_xp"]) for r in history],
        }
