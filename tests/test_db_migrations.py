import db


def _set_test_db(monkeypatch, tmp_path):
    test_db_path = tmp_path / "tracker.db"
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    return test_db_path


def test_init_db_applies_migrations_idempotently(monkeypatch, tmp_path):
    _set_test_db(monkeypatch, tmp_path)

    db.init_db()
    db.migrate_db()

    with db.get_conn() as conn:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(snapshots)").fetchall()
        }
        versions = {
            row["version"]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        skill_indexes = {
            row["name"] for row in conn.execute("PRAGMA index_list(skills)").fetchall()
        }

    assert "quest_points" not in columns
    assert {"quests_started", "quests_complete", "quests_not_started"} <= columns
    assert versions == {version for version, _ in db.MIGRATIONS}
    assert "idx_skills_snapshot_skill" in skill_indexes
