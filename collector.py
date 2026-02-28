import hashlib
import sqlite3
import time

import requests

from db import get_conn


def hash_activity(text, date):
    return hashlib.sha256(f"{text}|{date}".encode()).hexdigest()


USERNAME = "Varxis"
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


def collect_snapshot():
    r = requests.get(API_URL, timeout=15)
    data = r.json()

    if "skillvalues" not in data:
        print("Invalid response, skipping")
        return

    conn = get_conn()
    cur = conn.cursor()

    # Ensure player exists
    cur.execute("INSERT OR IGNORE INTO players (username) VALUES (?)", (USERNAME,))
    cur.execute("SELECT id FROM players WHERE username=?", (USERNAME,))
    player_id = cur.fetchone()["id"]

    # Insert snapshot
    cur.execute(
        """
        INSERT INTO snapshots (player_id, total_xp, total_level, overall_rank, combat_level, quest_points)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            player_id,
            data["totalxp"],
            data["totalskill"],
            int(data["rank"].replace(",", "")),
            data["combatlevel"],
            data["questsstarted"],
        ),
    )

    snapshot_id = cur.lastrowid

    # Insert skills
    for skill in data["skillvalues"]:
        skill_id = skill["id"]
        skill_name = SKILL_NAMES.get(skill_id, f"Unknown-{skill_id}")

        cur.execute(
            """
            INSERT INTO skills (snapshot_id, skill, level, xp, rank)
            VALUES (?, ?, ?, ?, ?)
        """,
            (snapshot_id, skill_name, skill["level"], skill["xp"], skill["rank"]),
        )

    # Insert activities
    for act in data.get("activities", []):
        h = hash_activity(act["text"], act["date"])
        try:
            cur.execute(
                "INSERT INTO activities (snapshot_id, text, date, hash) VALUES (?, ?, ?, ?)",
                (snapshot_id, act["text"], act["date"], h),
            )
        except sqlite3.IntegrityError:
            pass  # duplicate, ignore

    conn.commit()
    conn.close()

    # Print something useful
    print(
        f"Collected snapshot for {USERNAME} at {time.strftime('%Y-%m-%d %H:%M:%S')}, total XP: {data['totalxp']}, total level: {data['totalskill']}"
    )


if __name__ == "__main__":
    collect_snapshot()
