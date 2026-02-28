import os
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
# Database
# ---------------------------------------------------------------------------

DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH: Path = DATA_DIR / "tracker.db"
