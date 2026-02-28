import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "tracker.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY,
            player_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_xp INTEGER,
            total_level INTEGER,
            overall_rank INTEGER,
            combat_level INTEGER,
            quest_points INTEGER
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY,
            snapshot_id INTEGER,
            skill TEXT,
            level INTEGER,
            xp INTEGER,
            rank INTEGER
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,
            snapshot_id INTEGER,
            text TEXT,
            date TEXT,
            details TEXT,
            hash TEXT UNIQUE
        )
        """)
        cur = conn.execute("PRAGMA table_info(activities)")
        activity_columns = {row["name"] for row in cur.fetchall()}
        if "details" not in activity_columns:
            conn.execute("ALTER TABLE activities ADD COLUMN details TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_skills_snapshot_skill ON skills(snapshot_id, skill)"
        )
