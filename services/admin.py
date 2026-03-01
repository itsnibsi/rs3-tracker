"""
Admin service.

DB queries and data assembly for the admin dashboard.  Keeps the route
handler focused on HTTP concerns (auth, CSRF, rendering) rather than SQL.
"""

from db import get_conn


def get_admin_overview() -> dict:
    """Return table counts and latest snapshot timestamp for the admin page."""
    table_counts = []
    with get_conn() as conn:
        cur = conn.cursor()
        for table in ("players", "snapshots", "skills", "activities"):
            cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
            row = cur.fetchone()
            table_counts.append({"name": table, "count": row["count"]})

        cur.execute("SELECT timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 1")
        latest_row = cur.fetchone()

    latest_ts = None
    if latest_row:
        ts = latest_row["timestamp"]
        latest_ts = ts.isoformat() if hasattr(ts, "isoformat") else ts

    return {
        "db_path": "PostgreSQL (Neon)",
        "db_size_mb": "N/A",
        "latest_snapshot_ts": latest_ts,
        "table_counts": table_counts,
    }
