import hashlib
import os
import sqlite3
from datetime import datetime, timezone

import requests

from db import get_conn, init_db

USERNAME = os.getenv("RS3_USERNAME", "Varxis")
API_URL = f"https://apps.runescape.com/runemetrics/profile/profile?user={USERNAME}&activities=20"

SKILL_NAMES = {
    0: "Attack",
    1: "Defence",
    2: "Strength",
    3: "Constitution",
    4: "Ranged",
    5: "Prayer",
    6: "Magic",
    7: "Cooking",
    8: "Woodcutting",
    9: "Fletching",
    10: "Fishing",
    11: "Firemaking",
    12: "Crafting",
    13: "Smithing",
    14: "Mining",
    15: "Herblore",
    16: "Agility",
    17: "Thieving",
    18: "Slayer",
    19: "Farming",
    20: "Runecrafting",
    21: "Hunter",
    22: "Construction",
    23: "Summoning",
    24: "Dungeoneering",
    25: "Divination",
    26: "Invention",
    27: "Archaeology",
    28: "Necromancy",
}


def hash_activity(text, date, details):
    return hashlib.sha256(f"{text}|{date}|{details or ''}".encode()).hexdigest()


def legacy_hash_activity(text, date):
    return hashlib.sha256(f"{text}|{date}".encode()).hexdigest()


def to_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return default
        try:
            return int(cleaned)
        except ValueError:
            return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def collect_snapshot():
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return

    if "error" in data or "skillvalues" not in data:
        print(f"Invalid response or profile is private.")
        return

    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("INSERT OR IGNORE INTO players (username) VALUES (?)", (USERNAME,))
        cur.execute("SELECT id FROM players WHERE username=?", (USERNAME,))
        player_id = cur.fetchone()["id"]

        rank = to_int(data.get("rank"), 0)
        total_xp = to_int(data.get("totalxp"), 0)
        total_level = to_int(data.get("totalskill"), 0)
        combat_level = to_int(data.get("combatlevel"), 0)
        quests_started = to_int(data.get("questsstarted"), 0)
        quests_complete = to_int(data.get("questscomplete"), 0)
        quests_not_started = to_int(data.get("questsnotstarted"), 0)

        cur.execute(
            """
            INSERT INTO snapshots (
                player_id,
                total_xp,
                total_level,
                overall_rank,
                combat_level,
                quests_started,
                quests_complete,
                quests_not_started
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                player_id,
                total_xp,
                total_level,
                rank,
                combat_level,
                quests_started,
                quests_complete,
                quests_not_started,
            ),
        )
        snapshot_id = cur.lastrowid

        skills_data = []
        for skill in data["skillvalues"]:
            skill_name = SKILL_NAMES.get(skill["id"], f"Unknown-{skill['id']}")
            skills_data.append(
                (
                    snapshot_id,
                    skill_name,
                    to_int(skill.get("level"), 0),
                    to_int(skill.get("xp"), 0),
                    to_int(skill.get("rank"), 0),
                )
            )

        cur.executemany(
            "INSERT INTO skills (snapshot_id, skill, level, xp, rank) VALUES (?, ?, ?, ?, ?)",
            skills_data,
        )

        for act in data.get("activities", []):
            details = act.get("details")
            h = hash_activity(act["text"], act["date"], details)
            legacy_h = legacy_hash_activity(act["text"], act["date"])
            cur.execute(
                "SELECT 1 FROM activities WHERE hash IN (?, ?) LIMIT 1",
                (h, legacy_h),
            )
            if cur.fetchone():
                continue
            try:
                cur.execute(
                    "INSERT INTO activities (snapshot_id, text, date, details, hash) VALUES (?, ?, ?, ?, ?)",
                    (snapshot_id, act["text"], act["date"], details, h),
                )
            except sqlite3.IntegrityError:
                pass  # Duplicate activity, ignore

        conn.commit()
    print(
        f"Collected snapshot for {USERNAME} at {datetime.now(timezone.utc).isoformat()} - Total XP: {total_xp}"
    )


if __name__ == "__main__":
    init_db()
    collect_snapshot()
