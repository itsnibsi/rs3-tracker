import hashlib
import os
import sqlite3
from datetime import datetime, timezone

import requests

from db import get_conn

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


def hash_activity(text, date):
    return hashlib.sha256(f"{text}|{date}".encode()).hexdigest()


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

        rank = data.get("rank", "0")
        if isinstance(rank, str):
            rank = int(rank.replace(",", ""))

        cur.execute(
            """
            INSERT INTO snapshots (player_id, total_xp, total_level, overall_rank, combat_level, quest_points)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                player_id,
                data["totalxp"],
                data["totalskill"],
                rank,
                data["combatlevel"],
                data["questsstarted"],
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
                    skill["level"],
                    skill["xp"],
                    skill.get("rank", 0),
                )
            )

        cur.executemany(
            "INSERT INTO skills (snapshot_id, skill, level, xp, rank) VALUES (?, ?, ?, ?, ?)",
            skills_data,
        )

        for act in data.get("activities", []):
            h = hash_activity(act["text"], act["date"])
            try:
                cur.execute(
                    "INSERT INTO activities (snapshot_id, text, date, hash) VALUES (?, ?, ?, ?)",
                    (snapshot_id, act["text"], act["date"], h),
                )
            except sqlite3.IntegrityError:
                pass  # Duplicate activity, ignore

        conn.commit()
    print(
        f"Collected snapshot for {USERNAME} at {datetime.now(timezone.utc).isoformat()} - Total XP: {data['totalxp']}"
    )


if __name__ == "__main__":
    collect_snapshot()
