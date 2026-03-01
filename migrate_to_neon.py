import os
import sqlite3

import psycopg
from psycopg import sql

SQLITE_PATH = "./data/tracker.db"
DATABASE_URL = os.environ["DATABASE_URL"]

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

pg_conn = psycopg.connect(DATABASE_URL)

TABLES = ["players", "snapshots", "skills", "activities"]

with pg_conn.transaction():
    for table in TABLES:
        print(f"Migrating {table}...")

        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue

        columns = rows[0].keys()

        query = sql.SQL("""
            INSERT INTO {table} ({fields})
            VALUES ({values})
            ON CONFLICT DO NOTHING
        """).format(
            table=sql.Identifier(table),
            fields=sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )

        with pg_conn.cursor() as cursor:
            cursor.executemany(
                query, [tuple(row[col] for col in columns) for row in rows]
            )
        print(f"  {len(rows)} rows inserted")

    # Reset sequences so new inserts don't collide with migrated IDs
    for table in TABLES:
        pg_conn.execute(
            sql.SQL(
                "SELECT setval(pg_get_serial_sequence({table}, 'id'), COALESCE(MAX(id), 1)) FROM {tbl}"
            ).format(
                table=sql.Literal(table),
                tbl=sql.Identifier(table),
            )
        )
        print(f"  Reset sequence for {table}")

pg_conn.commit()
pg_conn.close()
sqlite_conn.close()
print("Migration complete.")
