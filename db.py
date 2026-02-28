import argparse
import sqlite3
from collections.abc import Callable

from config import DATA_DIR, DB_PATH  # noqa: F401 — re-exported for legacy imports
from log import get_logger

logger = get_logger(__name__)

MigrationFn = Callable[[sqlite3.Connection], None]


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cur.fetchall()}


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_migration_table(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)


def _is_migration_applied(conn: sqlite3.Connection, version: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ? LIMIT 1", (version,)
    )
    return cur.fetchone() is not None


def _mark_migration_applied(conn: sqlite3.Connection, version: str):
    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))


def _migration_add_activity_details(conn: sqlite3.Connection):
    if "details" not in _get_table_columns(conn, "activities"):
        conn.execute("ALTER TABLE activities ADD COLUMN details TEXT")


def _migration_snapshots_quest_fields(conn: sqlite3.Connection):
    columns = _get_table_columns(conn, "snapshots")
    if "quest_points" in columns and "quests_started" in columns:
        conn.execute("""
        UPDATE snapshots
        SET quests_started = COALESCE(quests_started, quest_points)
        """)

    if "quest_points" in columns and "quests_started" not in columns:
        conn.execute(
            "ALTER TABLE snapshots RENAME COLUMN quest_points TO quests_started"
        )
        columns = _get_table_columns(conn, "snapshots")

    if "quests_started" not in columns:
        conn.execute("ALTER TABLE snapshots ADD COLUMN quests_started INTEGER")
    if "quests_complete" not in columns:
        conn.execute("ALTER TABLE snapshots ADD COLUMN quests_complete INTEGER")
    if "quests_not_started" not in columns:
        conn.execute("ALTER TABLE snapshots ADD COLUMN quests_not_started INTEGER")

    conn.execute("""
    UPDATE snapshots
    SET
        quests_started = COALESCE(quests_started, 0),
        quests_complete = COALESCE(quests_complete, 0),
        quests_not_started = COALESCE(quests_not_started, 0)
    """)


def _migration_add_hash_to_activities(conn: sqlite3.Connection):
    if "hash" not in _get_table_columns(conn, "activities"):
        conn.execute("ALTER TABLE activities ADD COLUMN hash TEXT")


MIGRATIONS: list[tuple[str, MigrationFn]] = [
    ("20260228_01_activity_details", _migration_add_activity_details),
    ("20260228_02_snapshot_quest_fields", _migration_snapshots_quest_fields),
    ("20260228_03_activity_hash", _migration_add_hash_to_activities),
]


def run_migrations(conn: sqlite3.Connection):
    _ensure_migration_table(conn)
    for version, migration in MIGRATIONS:
        if _is_migration_applied(conn, version):
            continue
        logger.info("Applying migration: %s", version)
        migration(conn)
        _mark_migration_applied(conn, version)
        logger.info("Migration applied: %s", version)


def _create_base_tables(conn: sqlite3.Connection):
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
        quests_started INTEGER,
        quests_complete INTEGER,
        quests_not_started INTEGER
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


def _create_indexes(conn: sqlite3.Connection):
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_skills_snapshot_skill ON skills(snapshot_id, skill)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_hash ON activities(hash)"
    )


def init_db():
    with get_conn() as conn:
        _create_base_tables(conn)
        run_migrations(conn)
        _create_indexes(conn)
        conn.commit()


def migrate_db():
    with get_conn() as conn:
        _create_base_tables(conn)
        run_migrations(conn)
        _create_indexes(conn)
        conn.commit()


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Database initializer and migration runner"
    )
    parser.add_argument(
        "command",
        choices=("init", "migrate"),
        nargs="?",
        default="init",
        help="init creates base tables then applies migrations; migrate applies pending migrations only.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    from log import configure_logging

    configure_logging()
    args = _parse_args()
    if args.command == "migrate":
        migrate_db()
        logger.info("Migrations completed for %s", DB_PATH)
    else:
        init_db()
        logger.info("Database initialized at %s", DB_PATH)
