import asyncio
import hashlib
import sqlite3

import httpx

from config import RS3_USERNAME
from db import get_conn, init_db
from log import get_logger
from skills import SKILL_NAMES

logger = get_logger(__name__)

USERNAME = RS3_USERNAME
API_URL = f"https://apps.runescape.com/runemetrics/profile/profile?user={USERNAME}&activities=20"

# Global lock to prevent concurrent snapshot collections (e.g., background loop vs manual trigger)
_collection_lock = asyncio.Lock()


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


async def _fetch_runemetrics_data(client: httpx.AsyncClient, retries: int = 3):
    """Fetch data with exponential backoff for resilience."""
    for attempt in range(retries):
        try:
            r = await client.get(API_URL, timeout=15.0)
            r.raise_for_status()
            return r.json()
        except httpx.RequestError as e:
            logger.warning(
                "RuneMetrics API request failed (attempt %d/%d): %s",
                attempt + 1,
                retries,
                e,
            )
            if attempt == retries - 1:
                logger.error("All retries failed for RuneMetrics API.")
                return None
            await asyncio.sleep(2**attempt)  # 1s, 2s, 4s...
    return None


async def collect_snapshot():
    """Asynchronous collector that safely blocks concurrent runs."""
    async with _collection_lock:
        async with httpx.AsyncClient() as client:
            data = await _fetch_runemetrics_data(client)

        if not data:
            return

        if "error" in data or "skillvalues" not in data:
            logger.warning(
                "Invalid RuneMetrics response for user %s — profile may be private",
                USERNAME,
            )
            return

        # Execute DB inserts synchronously (SQLite handles this instantly with WAL mode)
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute(
                "INSERT OR IGNORE INTO players (username) VALUES (?)", (USERNAME,)
            )
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

        logger.info(
            "Snapshot collected for %s — total XP: %s",
            USERNAME,
            total_xp,
        )


if __name__ == "__main__":
    init_db()
    asyncio.run(collect_snapshot())
