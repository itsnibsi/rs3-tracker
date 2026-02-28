"""
Tests for admin route security: CSRF verification and per-IP rate limiting.
"""

import secrets
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import db
import routes.admin as admin_mod
from app import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ADMIN_USER = "testadmin"
ADMIN_PASS = "testpass"
VALID_CREDS = (ADMIN_USER, ADMIN_PASS)


@pytest.fixture(autouse=True)
def _patch_admin_creds(monkeypatch):
    monkeypatch.setattr(admin_mod, "ADMIN_USERNAME", ADMIN_USER)
    monkeypatch.setattr(admin_mod, "ADMIN_PASSWORD", ADMIN_PASS)


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch, tmp_path):
    test_db_path = tmp_path / "tracker.db"
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _csrf_cookies_and_token(client: TestClient) -> tuple[dict, str]:
    """Hit GET /admin to obtain a valid CSRF cookie + token string."""
    resp = client.get("/admin", auth=VALID_CREDS)
    assert resp.status_code == 200
    csrf_token = resp.cookies.get(admin_mod._CSRF_COOKIE)
    assert csrf_token, "No CSRF cookie set on GET /admin"
    return {admin_mod._CSRF_COOKIE: csrf_token}, csrf_token


# ---------------------------------------------------------------------------
# CSRF tests
# ---------------------------------------------------------------------------


class TestCsrf:
    def test_get_admin_sets_csrf_cookie(self, client):
        resp = client.get("/admin", auth=VALID_CREDS)
        assert resp.status_code == 200
        assert admin_mod._CSRF_COOKIE in resp.cookies

    def test_post_maintenance_valid_csrf_succeeds(self, client):
        cookies, token = _csrf_cookies_and_token(client)
        with patch("routes.admin.collect_snapshot"):
            resp = client.post(
                "/admin/maintenance/update",
                auth=VALID_CREDS,
                cookies=cookies,
                data={admin_mod._CSRF_FIELD: token},
            )
        assert resp.status_code == 200

    def test_post_maintenance_missing_csrf_fails(self, client):
        resp = client.post(
            "/admin/maintenance/update",
            auth=VALID_CREDS,
            data={},  # no csrf_token field
        )
        # FastAPI will return 422 (missing required field) before we even reach
        # our _verify_csrf check, which is the correct behaviour.
        assert resp.status_code in {403, 422}

    def test_post_maintenance_wrong_csrf_fails(self, client):
        cookies, _token = _csrf_cookies_and_token(client)
        resp = client.post(
            "/admin/maintenance/update",
            auth=VALID_CREDS,
            cookies=cookies,
            data={admin_mod._CSRF_FIELD: secrets.token_hex(32)},  # wrong value
        )
        assert resp.status_code == 403

    def test_post_sql_valid_csrf(self, client):
        cookies, token = _csrf_cookies_and_token(client)
        resp = client.post(
            "/admin/sql",
            auth=VALID_CREDS,
            cookies=cookies,
            data={admin_mod._CSRF_FIELD: token, "sql": "SELECT 1"},
        )
        assert resp.status_code == 200

    def test_post_sql_missing_cookie_fails(self, client):
        """If the CSRF cookie is absent the token comparison must fail."""
        resp = client.post(
            "/admin/sql",
            auth=VALID_CREDS,
            # no cookies kwarg — cookie absent
            data={admin_mod._CSRF_FIELD: secrets.token_hex(32), "sql": "SELECT 1"},
        )
        assert resp.status_code == 403

    def test_csrf_token_refreshed_on_each_response(self, client):
        """Every admin response must set (or re-set) the CSRF cookie."""
        resp = client.get("/admin", auth=VALID_CREDS)
        assert admin_mod._CSRF_COOKIE in resp.cookies


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_rate_limit_triggers_after_max_requests(self, client, monkeypatch):
        """Exceed the per-IP window limit and expect 429."""
        monkeypatch.setattr(admin_mod, "ADMIN_RATE_LIMIT", 3)
        # Clear any accumulated state from other tests.
        admin_mod._ip_log.clear()

        for _ in range(3):
            resp = client.get("/admin", auth=VALID_CREDS)
            assert resp.status_code == 200

        resp = client.get("/admin", auth=VALID_CREDS)
        assert resp.status_code == 429

    def test_rate_limit_is_per_ip(self, client, monkeypatch):
        """Requests from different IPs should have independent counters."""
        monkeypatch.setattr(admin_mod, "ADMIN_RATE_LIMIT", 2)
        admin_mod._ip_log.clear()

        # Exhaust limit for 127.0.0.1
        for _ in range(2):
            client.get("/admin", auth=VALID_CREDS)

        # Simulate a different IP by patching _client_ip
        with patch("routes.admin._client_ip", return_value="10.0.0.1"):
            resp = client.get("/admin", auth=VALID_CREDS)
        assert resp.status_code == 200
