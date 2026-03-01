import argparse
import os
from collections.abc import Callable

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import DATA_DIR, DB_PATH  # noqa: F401 — kept for API compatibility
from log import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

# Global connection pool
pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=5,
    kwargs={"row_factory": dict_row},
)

MigrationFn = Callable[[psycopg.Connection], None]


def get_conn():
    # identical external API: returns context-manageable connection
    return pool.connection()


def _get_table_columns(conn: psycopg.Connection, table_name: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            """,
            (table_name,),
        )
        return {row[0] for row in cur.fetchall()}


def _ensure_migration_table(conn: psycopg.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _is_migration_applied(conn: psycopg.Connection, version: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = %s LIMIT 1",
        (version,),
    )
    return cur.fetchone() is not None


def _mark_migration_applied(conn: psycopg.Connection, version: str):
    conn.execute(
        "INSERT INTO schema_migrations (version) VALUES (%s)",
        (version,),
    )


# ----------------------
# Migrations
# ---------------------


MIGRATIONS: list[tuple[str, MigrationFn]] = []


def run_migrations(conn: psycopg.Connection):
    _ensure_migration_table(conn)

    for version, migration in MIGRATIONS:
        if _is_migration_applied(conn, version):
            continue

        logger.info("Applying migration: %s", version)
        migration(conn)
        _mark_migration_applied(conn, version)
        logger.info("Migration applied: %s", version)


# ----------------------
# Base schema
# ----------------------


def _create_base_tables(conn: psycopg.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            id BIGSERIAL PRIMARY KEY,
            username TEXT UNIQUE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id BIGSERIAL PRIMARY KEY,
            player_id BIGINT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_xp BIGINT,
            total_level INTEGER,
            overall_rank INTEGER,
            combat_level INTEGER,
            quests_started INTEGER,
            quests_complete INTEGER,
            quests_not_started INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skills (
            id BIGSERIAL PRIMARY KEY,
            snapshot_id BIGINT,
            skill TEXT,
            level INTEGER,
            xp BIGINT,
            rank INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id BIGSERIAL PRIMARY KEY,
            snapshot_id BIGINT,
            text TEXT,
            date TEXT,
            details TEXT,
            hash TEXT UNIQUE
        )
        """
    )


def _create_indexes(conn: psycopg.Connection):
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
        run_migrations(conn)
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
    )
    return parser.parse_args()


if __name__ == "__main__":
    from log import configure_logging

    configure_logging()
    args = _parse_args()

    if args.command == "migrate":
        migrate_db()
        logger.info("Migrations completed")
    else:
        init_db()
        logger.info("Database initialized")
