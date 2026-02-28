import os
import secrets
from pathlib import Path

# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

RS3_USERNAME: str = os.getenv("RS3_USERNAME", "Varxis")

# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

ADMIN_USERNAME: str | None = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD: str | None = os.getenv("ADMIN_PASSWORD")

# ---------------------------------------------------------------------------
# Security — CSRF
# ---------------------------------------------------------------------------

# Used to sign CSRF tokens.  Stable across restarts when provided via env;
# falls back to a random value (tokens invalidated on every restart, which is
# acceptable for a single-instance personal app).
SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_hex(32))

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH: Path = DATA_DIR / "tracker.db"
