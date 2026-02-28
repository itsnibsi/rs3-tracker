import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "tracker.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE
    )
    """)

    cur.execute("""
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY,
        snapshot_id INTEGER,
        skill TEXT,
        level INTEGER,
        xp INTEGER,
        rank INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY,
        snapshot_id INTEGER,
        text TEXT,
        date TEXT,
        hash TEXT
    )
    """)

    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_hash ON activities(hash);
    """)

    conn.commit()
    conn.close()
