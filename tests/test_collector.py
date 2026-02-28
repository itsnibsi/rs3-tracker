import collector
import db


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _set_test_db(monkeypatch, tmp_path):
    test_db_path = tmp_path / "tracker.db"
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    return test_db_path


def test_collect_snapshot_persists_quest_fields(monkeypatch, tmp_path):
    _set_test_db(monkeypatch, tmp_path)
    db.init_db()

    payload = {
        "rank": "123",
        "totalxp": "1,000",
        "totalskill": "2500",
        "combatlevel": "138",
        "questsstarted": "250",
        "questscomplete": "180",
        "questsnotstarted": "70",
        "skillvalues": [
            {"id": 0, "level": 99, "xp": "13,034,431", "rank": 1000},
            {"id": 1, "level": 99, "xp": "13,034,431", "rank": 1001},
        ],
        "activities": [],
    }

    monkeypatch.setattr(collector, "USERNAME", "TestUser")
    monkeypatch.setattr(collector.requests, "get", lambda *_args, **_kwargs: _FakeResponse(payload))

    collector.collect_snapshot()

    with db.get_conn() as conn:
        row = conn.execute(
            """
            SELECT quests_started, quests_complete, quests_not_started
            FROM snapshots
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row["quests_started"] == 250
    assert row["quests_complete"] == 180
    assert row["quests_not_started"] == 70
