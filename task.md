how can I configure this project to use supabase and migrate the data from sqlite3 (from local env) to over there: #### web.py
```python
"""
Shared Jinja2Templates instance.

Import from here so both route modules use the same object and template
directory is declared in exactly one place.
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
```

#### utils.py
```python
from skills import EXTENDED_120_SKILLS

XP_PRECISION = 10

# Optional exact cumulative XP table for Invention.
# Index by level (e.g. index 0 => level 1 cumulative XP, index 119 => level 120).
INVENTION_XP_TABLE = [
    0,
    830,
    1861,
    2902,
    3980,
    5126,
    6390,
    7787,
    9400,
    11275,
    13605,
    16372,
    19656,
    23546,
    28138,
    33520,
    39809,
    47109,
    55535,
    64802,
    77190,
    90811,
    106221,
    123573,
    143025,
    164742,
    188893,
    215651,
    245196,
    277713,
    316311,
    358547,
    404634,
    454796,
    509259,
    568254,
    632019,
    700797,
    774834,
    854383,
    946227,
    1044569,
    1149696,
    1261903,
    1381488,
    1508756,
    1644015,
    1787581,
    1939773,
    2100917,
    2283490,
    2476369,
    2679907,
    2894505,
    3120508,
    3358307,
    3608290,
    3870846,
    4146374,
    4435275,
    4758122,
    5096111,
    5449685,
    5819299,
    6205407,
    6608473,
    7028964,
    7467354,
    7924122,
    8399751,
    8925664,
    9472665,
    10041285,
    10632061,
    11245538,
    11882262,
    12542789,
    13227679,
    13937496,
    14672812,
    15478994,
    16313404,
    17176661,
    18069395,
    18992239,
    19945833,
    20930821,
    21947856,
    22997593,
    24080695,
    25259906,
    26475754,
    27728955,
    29020233,
    30350318,
    31719944,
    33129852,
    34580790,
    36073511,
    37608773,
    39270442,
    40978509,
    42733789,
    44537107,
    46389643,
    48291180,
    50243611,
    52247435,
    54303504,
    56412678,
    58575823,
    60793812,
    63067521,
    65397835,
    67785643,
    70231841,
    72737330,
    75303019,
    77929820,
    80618654,
]


def _is_max_level(skill: str, level: int) -> bool:
    return level >= 120 or (level >= 99 and skill not in EXTENDED_120_SKILLS)


def _standard_xp(level: int) -> int:
    total = 0
    for i in range(1, level):
        total += int(i + 300 * (2 ** (i / 7.0)))
    return total // 4


def _invention_xp(level: int) -> int:
    idx = level - 1
    if 0 <= idx < len(INVENTION_XP_TABLE):
        return int(INVENTION_XP_TABLE[idx])
    # Fallback approximation until table is provided
    return int(36000000 * ((level / 99.0) ** 3.5))


def xp_to_next_level(skill: str, level: int, xp: int) -> int:
    if _is_max_level(skill, level):
        return 0

    normalized_xp = xp / XP_PRECISION
    if skill == "Invention":
        next_level_xp = _invention_xp(level + 1)
    else:
        next_level_xp = _standard_xp(level + 1)

    remaining = max(0.0, next_level_xp - normalized_xp)
    return int(round(remaining * XP_PRECISION))


def calculate_progress(skill: str, level: int, xp: int) -> float:
    normalized_xp = xp / XP_PRECISION

    # Handle max levels (120 caps vs 99 caps)
    if _is_max_level(skill, level):
        return 1.0

    if skill == "Invention":
        current_level_xp = _invention_xp(level)
        next_level_xp = _invention_xp(level + 1)
    else:
        current_level_xp = _standard_xp(level)
        next_level_xp = _standard_xp(level + 1)

    if normalized_xp >= next_level_xp or next_level_xp == current_level_xp:
        return 1.0

    progress = (normalized_xp - current_level_xp) / (next_level_xp - current_level_xp)
    return max(0.0, min(1.0, progress))
```

#### skills.py
```python
# ---------------------------------------------------------------------------
# Canonical skill and activity taxonomy metadata for RS3.
# All other modules should import from here — never redeclare these constants.
# ---------------------------------------------------------------------------

# Maps RuneMetrics skill ID -> skill name.
SKILL_NAMES: dict[int, str] = {
    0: "Attack",
    1: "Defence",
    2: "Strength",
    3: "Constitution",
    4: "Ranged",
    5: "Prayer",
    6: "Magic",
    7: "Cooking",
    8: "Woodcutting",
    9: "Fletching",
    10: "Fishing",
    11: "Firemaking",
    12: "Crafting",
    13: "Smithing",
    14: "Mining",
    15: "Herblore",
    16: "Agility",
    17: "Thieving",
    18: "Slayer",
    19: "Farming",
    20: "Runecrafting",
    21: "Hunter",
    22: "Construction",
    23: "Summoning",
    24: "Dungeoneering",
    25: "Divination",
    26: "Invention",
    27: "Archaeology",
    28: "Necromancy",
}

# Display order matching the in-game skills interface.
RS3_ORDER: list[str] = [
    "Attack",
    "Constitution",
    "Mining",
    "Strength",
    "Agility",
    "Smithing",
    "Defence",
    "Herblore",
    "Fishing",
    "Ranged",
    "Thieving",
    "Cooking",
    "Prayer",
    "Crafting",
    "Firemaking",
    "Magic",
    "Fletching",
    "Woodcutting",
    "Runecrafting",
    "Slayer",
    "Farming",
    "Construction",
    "Hunter",
    "Summoning",
    "Dungeoneering",
    "Divination",
    "Invention",
    "Archaeology",
    "Necromancy",
]

# Skills whose level cap is 120 rather than 99.
EXTENDED_120_SKILLS: list[str] = [
    "Dungeoneering",
    "Invention",
    "Archaeology",
    "Farming",
    "Herblore",
    "Slayer",
    "Necromancy",
]

# Per-skill accent colours used in charts and cards.
SKILL_COLORS: dict[str, str] = {
    "Attack": "#b04d3f",
    "Constitution": "#a43f52",
    "Mining": "#7a6f63",
    "Strength": "#b85d3d",
    "Agility": "#5c8b6d",
    "Smithing": "#7c7063",
    "Defence": "#7f8b97",
    "Herblore": "#4f7f4f",
    "Fishing": "#4f758f",
    "Ranged": "#6b7f52",
    "Thieving": "#6c5a48",
    "Cooking": "#a36a3a",
    "Prayer": "#b9ae8d",
    "Crafting": "#9f7b60",
    "Firemaking": "#b85a32",
    "Magic": "#5e6fb0",
    "Fletching": "#7b6c54",
    "Woodcutting": "#5f7a4f",
    "Runecrafting": "#6e5d9b",
    "Slayer": "#8b4a4a",
    "Farming": "#64834c",
    "Construction": "#8a6b4f",
    "Hunter": "#7a6f54",
    "Summoning": "#8c4f7f",
    "Dungeoneering": "#5e5f67",
    "Divination": "#4e7f89",
    "Invention": "#88724f",
    "Archaeology": "#927154",
    "Necromancy": "#6f5b8f",
}

# Activity classification: type key -> display label + accent colour.
ACTIVITY_TYPE_META: dict[str, dict[str, str]] = {
    "quest": {"label": "Quest", "color": "#9ecb67"},
    "clue": {"label": "Clue", "color": "#a48ad8"},
    "level": {"label": "Level Up", "color": "#69a8ff"},
    "kill": {"label": "Kill", "color": "#d78070"},
    "loot": {"label": "Loot", "color": "#d1b366"},
    "achievement": {"label": "Achievement", "color": "#95b999"},
    "unlock": {"label": "Unlock", "color": "#6ec2bb"},
    "activity": {"label": "Activity", "color": "#8da0b6"},
}
```

#### REVIEW.md
``````markdown
# RS3 Tracker Architectural Review

Scope: full repository review with focus on maintainability, extension speed, structural clarity, runtime behavior, and practical security for a personal-use Cloud Run app.

## General project structure and organization

1. Problem: the project has clear functional separation at file level (`app.py`, `collector.py`, `db.py`, `utils.py`) but the operational center is a single 1000+ line `app.py`.
Suggested improvement: split into small modules by responsibility (`routes`, `services`, `repositories`, `domain/models`, `config`) while keeping behavior unchanged.

2. Problem: there is no explicit architecture boundary between web rendering, API shaping, data access, and analytics calculations.
Suggested improvement: introduce a service layer for dashboard/chart calculations and keep routes thin (parse input, call service, return response).

3. Problem: deployment and runtime hygiene are weak (`.dockerignore` is empty, no CI checks, no tests), which increases drift and accidental breakage risk.
Suggested improvement: add a minimal CI pipeline (lint + tests + build), and harden Docker context filtering (`.venv`, `.git`, `data/`, caches, local artifacts).

4. Problem: schema evolution is done ad hoc in `init_db()` (single ALTER guard), not through a migration mechanism.
Suggested improvement: add migration tooling (Alembic-like workflow for SQLite or lightweight SQL migration runner), and run schema changes only through explicit reviewed migration steps.

5. Problem: observability is print-based and inconsistent.
Suggested improvement: move to structured logging with log levels, request context, and collector event IDs for fast diagnosis.

## backend organization

1. Problem: `app.py` combines configuration constants, time-bucket math, dashboard assembly, API handlers, admin handlers, and background scheduling.
Suggested improvement: split into:
- `config.py` for env/config parsing
- `db/repository.py` for SQL I/O
- `services/dashboard.py`, `services/charts.py`, `services/collector_runner.py`
- `routes/public.py`, `routes/admin.py`

2. Problem: domain constants are duplicated across modules (`SKILL_NAMES`, `RS3_ORDER`, color map), making future feature changes error-prone.
Suggested improvement: define one canonical skill metadata source (name, order, color, icon key, cap rules) and import it everywhere.

3. Problem: route handlers contain heavy data transformation logic directly.
Suggested improvement: convert handlers into orchestration only; move compute logic to pure functions that are easy to test.

4. Problem: background collector scheduling is embedded in app lifespan, tightly coupling ingestion to web process lifecycle.
Suggested improvement: run ingestion as a dedicated scheduled trigger (Cloud Scheduler -> authenticated endpoint or Cloud Run Job), and keep optional manual trigger in admin.

5. Problem: `get_conn()` sets WAL on every connection and uses `check_same_thread=False` by default.
Suggested improvement: configure DB pragmas once at startup and create simple connection factory methods for read/write operations with explicit intent.

## backend logic

1. Problem: quest-related metric semantics are currently incorrect (`quest_points` is sourced from `questsstarted`), and naming no longer reflects real API data.
Suggested improvement: rename and store the actual fields as `quests_started`, `quests_complete`, and `quests_not_started`, then update collector ingestion to map those fields explicitly from RuneMetrics profile payload. If/when you add quests endpoint ingestion, keep it as a separate enrichment layer rather than overloading snapshot semantics.

2. Problem: multiple time-window/bucket paths (`get_timeframe_window`, `get_period_window`, multiple aggregators) overlap and diverge.
Suggested improvement: unify windowing and bucketing behind one tested API (`TimeWindowSpec` + generic aggregator).

3. Problem: there is dead/legacy behavior still present (`build_bucket_totals` unused, some API endpoints not used by frontend).
Suggested improvement: remove unused functions/routes or explicitly mark them as retained API surface with tests and consumers.

4. Problem: collector inserts snapshots each run without idempotency key for snapshot granularity.
Suggested improvement: add ingestion idempotency at service level (for example “skip insert if latest snapshot is too recent and unchanged”) without touching schema first.

5. Problem: collector and update paths catch broad exceptions and mostly print, which can hide partial failure causes.
Suggested improvement: narrow exception handling (network vs parse vs DB), return typed errors, and include actionable log messages.

## backend performance

1. Problem: dashboard request loads all activities and sorts in Python on every page load.
Suggested improvement: query only needed activity window (for example recent N days or N rows) and perform ordering/filtering in SQL.

2. Problem: chart endpoints fetch large historical rowsets and bucket in Python; repeated `datetime.strptime` parsing adds CPU overhead.
Suggested improvement: push more aggregation into SQL where practical, or cache pre-parsed timestamp/value arrays in a service-level memo for hot paths.

3. Problem: skills totals endpoint loads all skills/timepoints then groups in Python, which scales poorly with history growth.
Suggested improvement: scope by requested period early in SQL and query per skill only when needed.

4. Problem: index strategy is partial for current query patterns.
Suggested improvement: add/query-review indexes based on real access paths (`skills(skill, snapshot_id)` and activity date indexes if feed keeps growing). Coordinate any schema/index change separately.

5. Problem: collector scheduling inside web container can cause duplicate runs across instances and nondeterministic timing when Cloud Run scales.
Suggested improvement: move schedule orchestration outside the request-serving process.

## backend security

1. Problem: `/api/update` is publicly callable, but this is currently an intentional product decision for your personal workflow.
Suggested improvement: keep current behavior unchanged for now; revisit when you define rate-limit/abuse policy.

2. Problem: admin forms rely on HTTP Basic without CSRF protection for state-changing actions.
Suggested improvement: add CSRF token verification for admin POST actions, even for personal deployments.

3. Problem: SQL console is intentionally powerful but high risk if admin creds leak.
Suggested improvement: keep console but add explicit “read-only mode” default plus an opt-in write toggle.

4. Problem: admin credentials are env-based and should be rotated safely in production.
Suggested improvement: move `ADMIN_USERNAME` and `ADMIN_PASSWORD` to Secret Manager and bind them directly to Cloud Run env vars. Practical flow:
- create secrets (`gcloud secrets create ...`, `gcloud secrets versions add ...`)
- grant service account access (`roles/secretmanager.secretAccessor`)
- bind in deploy/update (`--set-secrets ADMIN_USERNAME=...,ADMIN_PASSWORD=...`)

5. Problem: no explicit rate limiting or brute-force resistance on admin endpoints.
Suggested improvement: add simple per-IP throttling middleware or Cloud Armor rules for admin paths; keep `/api/update` unchanged until you decide policy.

6. Problem: SQLite on Cloud storage mounts can be sensitive to locking semantics depending on mount mode and concurrency pattern.
Suggested improvement: treat this as a verification task (not a blocker): validate your current mount mode with a short concurrency/integrity check and keep WAL/checkpoint maintenance in your admin toolbox.

## frontend organization

1. Problem: `templates/index.html` contains a large inline script (charting, feed rendering, modal control, API calls) with no module boundaries.
Suggested improvement: move JS into `static/js/` modules (`dashboard.js`, `feed.js`, `charts.js`, `modal.js`) and keep template mostly declarative.

2. Problem: template mixes layout and behavior heavily, which slows feature work.
Suggested improvement: use data attributes + small initialization functions, and keep all imperative logic in JS modules.

3. Problem: many inline style attributes in templates reduce reuse and consistency.
Suggested improvement: convert inline styles to named utility/component classes.

4. Problem: public API surface includes endpoints not used by current UI.
Suggested improvement: either wire them into UI intentionally or remove/deprecate to reduce maintenance surface.

## frontend logic

1. Problem: update and chart fetch paths have minimal error handling; failures can leave UI in ambiguous states.
Suggested improvement: add robust fetch error handling, timeout handling, and visible error states/toasts.

2. Problem: activity type count logic creates elements but never appends them, indicating incomplete behavior.
Suggested improvement: either complete the UI target for counts or delete dead logic.

3. Problem: modal interactions are mouse-centric and miss keyboard/accessibility controls.
Suggested improvement: add Escape-to-close, focus trapping, and ARIA labels/roles.

4. Problem: activity feed rendering is full rebuild every time data changes.
Suggested improvement: keep it for now (simple/personal), but isolate rendering into pure functions so incremental rendering can be added later if needed.

5. Problem: automated frontend tests are currently absent.
Suggested improvement: defer frontend test automation for now by decision, and maintain a short manual regression checklist until priorities shift.

## frontend performance

1. Problem: page includes heavy CDN dependencies (`chart.js`, `moment`, `chartjs-adapter-moment`) synchronously in head.
Suggested improvement: self-host and defer scripts; replace Moment with `chartjs-adapter-date-fns` (recommended lightweight default) or `chartjs-adapter-luxon` if you need stronger timezone/date features. If you do not need time-scale parsing in-browser, pre-format labels server-side and drop date adapters entirely.

2. Problem: all activity data is embedded into HTML payload (`tojson`) and grows with history.
Suggested improvement: fetch activities on demand with pagination/windowing API.

3. Problem: single huge HTML+JS response is less cacheable than split static assets.
Suggested improvement: move JS to static files so browser caching works across requests.

4. Problem: some UI transitions use `transition: all`, which can trigger avoidable repaints.
Suggested improvement: transition specific properties only (`transform`, `border-color`, etc.).

## styling standards

1. Problem: CSS is one large global file with mixed paradigms and some stale selectors.
Suggested improvement: organize styles by component sections and remove unused selectors regularly.

2. Problem: design tokens exist but are not consistently applied (hardcoded colors/sizing still appear).
Suggested improvement: standardize color/spacing/typography tokens and enforce their usage.

3. Problem: naming style is generally readable but not systematic enough for long-term growth.
Suggested improvement: adopt a naming convention (component-prefix or BEM-lite) and document it briefly.

4. Problem: style and behavior coupling appears in templates (inline styles + script assumptions).
Suggested improvement: keep styling concerns in CSS and behavior hooks in explicit `data-*` attributes.

5. Problem: no CSS linting/quality gate.
Suggested improvement: add Stylelint with a minimal config to preserve consistency without over-policing.

## Refactor Task List (from current state to clean baseline)

1. Freeze current behavior with a short regression checklist (dashboard loads, manual update works, admin SQL works, collector ingests).
2. Add a safety branch and snapshot DB backup workflow for local and Cloud Run environments.
3. Add `.dockerignore` and clean container context to avoid shipping local artifacts.
4. Introduce `config.py` and centralize all env/config parsing with defaults and validation.
5. Extract canonical domain metadata for skills/activity taxonomy into one module.
6. Create repository layer for DB queries; move raw SQL out of route handlers.
7. Create service layer for dashboard assembly and chart/window aggregation.
8. Split routes into `public` and `admin` modules; keep `app.py` as composition root only.
9. Replace print-based logging with structured logging and consistent error categories.
10. Plan and execute a schema migration for quest fields: rename `quest_points` to `quests_started`, and add `quests_complete` + `quests_not_started` (migration reviewed with you before rollout).
11. Update collector ingestion and snapshot serialization to use the new quest field mapping from RuneMetrics profile payload.
12. Add CSRF protection for admin POST actions and basic rate limiting for admin endpoints; keep `/api/update` policy unchanged for now.
13. Integrate Google Secret Manager for admin credentials in Cloud Run deployment and document the exact deploy command pattern.
14. Separate collector scheduling from web lifecycle (Cloud Scheduler or Cloud Run Job), preserving manual trigger fallback.
15. Add targeted query/index improvements for current hot paths (especially activities and skill history queries). Discuss any schema/index migrations with you before applying.
16. Move inline frontend script into `static/js` modules and keep templates mostly markup.
17. Add frontend loading/error states, accessibility upgrades (keyboard/focus/ARIA), and remove dead JS branches.
18. Reduce frontend payload growth by loading activity feed via API with server-side limits.
19. Self-host/defer frontend chart scripts and replace Moment adapter (prefer `date-fns` adapter unless Luxon requirements emerge).
20. Split/organize CSS by component blocks, remove stale selectors, and eliminate inline styles.
21. Add lightweight automated checks in CI: `ruff`/lint, minimal backend tests, and Docker build validation.
22. Document architecture and operational runbook (`README` update: ingestion flow, deployment behavior, admin safety, secret handling).
23. Execute incremental rollout: module split first, data-model cleanup second, security hardening third, performance changes fourth, UI cleanup fifth, then stabilization pass.

---

Q: What's your main priority right now?
A: I think we should prioritize things we can do without affecting many different places, and get those out of the way before we start working on code splitting and a new frontend and performance.

Q: How do you want to work through this?
A: Break related items into clear chunks, give me the plan per chunk and then execute in order on my command

---

Current work task list, in order (finished chunks marked with **FINISHED**):

 **FINISHED** **Chunk A — Constants & config consolidation** *(items 4, 5)*
Extract `config.py` for all env/config parsing, and create one canonical skill metadata module (names, order, colors, icon keys, cap rules). Zero logic change — just moving things to the right home before the module split touches them. Do this first so the split has clean imports to work with.

 **FINISHED** **Chunk B — Structured logging** *(item 9)*
Replace all `print()` calls with `logging` (structured, leveled). Isolated change, no behavior impact, makes every subsequent chunk easier to debug.

**Chunk C — Security hardening** *(item 12)*
CSRF tokens on admin POST actions, basic per-IP rate limiting middleware on admin endpoints. Touches only admin routes — no public surface change.

**Chunk D — Backend module split** *(items 1, 2, 6, 7, 8)*
Split `app.py` into `config` (already done in A), `db/repository.py`, `services/dashboard.py` + `services/charts.py`, `routes/public.py` + `routes/admin.py`, with `app.py` as thin composition root. This is the biggest chunk and the riskiest — doing it after A/B/C means imports and logging are already clean.

**Chunk E — Collector & performance** *(items 14, 15)*
Decouple collector scheduling from web lifecycle. Add targeted query/index improvements for hot paths. Depends on D being done so the repository layer is in place.

**Chunk F — Frontend** *(items 16, 17, 18, 19, 20)*
JS into static modules, loading/error states + accessibility, activity feed via paginated API, replace Moment adapter, CSS cleanup. Fully isolated from backend — can overlap with E if needed.

**Chunk G — Documentation** *(item 22)*
README update covering architecture, ingestion flow, deployment, admin safety. Do last so it reflects the final state.
``````

#### README.md
``````markdown
## Admin page

The app exposes a protected admin page at `/admin` with:

- A SQL console (single statement per run, max 200 result rows shown)
- Snapshot collection trigger
- SQLite maintenance actions (`VACUUM`, WAL checkpoint)
- Basic DB overview (table row counts, DB size, latest snapshot timestamp)

### Configure admin auth (outside git)

Set these environment variables in Cloud Run:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

If either is missing, `/admin` returns `503` and stays disabled.

### Option A: direct env vars (quick setup)

```bash
gcloud run services update rs3-tracker \
  --region=europe-north1 \
  --set-env-vars=ADMIN_USERNAME=admin,ADMIN_PASSWORD='change-me'
```

### Option B: Secret Manager (recommended)

1. Create secrets and add values:

```bash
printf 'admin' | gcloud secrets create rs3-admin-username --data-file=- --replication-policy=automatic
printf 'change-me' | gcloud secrets create rs3-admin-password --data-file=- --replication-policy=automatic
```

If the secrets already exist, add new versions instead:

```bash
printf 'admin' | gcloud secrets versions add rs3-admin-username --data-file=-
printf 'change-me' | gcloud secrets versions add rs3-admin-password --data-file=-
```

2. Grant your Cloud Run runtime service account access:

```bash
SERVICE_ACCOUNT="$(gcloud run services describe rs3-tracker \
  --region=europe-north1 \
  --format='value(spec.template.spec.serviceAccountName)')"

if [ -z "${SERVICE_ACCOUNT}" ]; then
  PROJECT_NUMBER="$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')"
  SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

gcloud secrets add-iam-policy-binding rs3-admin-username \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding rs3-admin-password \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

3. Bind the secrets to env vars on the service:

```bash
gcloud run services update rs3-tracker \
  --region=europe-north1 \
  --set-secrets=ADMIN_USERNAME=rs3-admin-username:latest,ADMIN_PASSWORD=rs3-admin-password:latest
```

### Cloud Build integration

`cloudbuild.yaml` now supports optional substitutions for admin secrets:

- `_ADMIN_USERNAME_SECRET`
- `_ADMIN_PASSWORD_SECRET`

Set both in your Cloud Build trigger (for example `rs3-admin-username` and `rs3-admin-password`) to auto-bind secrets on every deploy.
If you leave them empty, deploy still succeeds, but admin auth vars must already exist on the service (or `/admin` stays disabled).

## Schema migrations

The app now uses versioned SQLite migrations tracked in `schema_migrations`.

- `init_db()` creates base tables and applies pending migrations.
- FastAPI startup already calls `init_db()`, so new revisions apply pending migrations automatically when the container starts.
- You can also run migrations manually:

```bash
python db.py migrate
```

Current migration includes snapshot quest field cleanup:

- Renames `snapshots.quest_points` -> `snapshots.quests_started`
- Adds `snapshots.quests_complete`
- Adds `snapshots.quests_not_started`

### Cloud Run rollout checklist for schema changes

1. Deploy code that includes the migration.
2. Keep at least one instance start after deploy (startup runs migrations).
3. Verify logs for migration success.
4. Validate schema quickly from admin SQL console:

```sql
PRAGMA table_info(snapshots);
```

For future schema changes, add a new migration entry in `db.py` and avoid editing old migration steps.

## Automated checks

GitHub Actions workflow: `.github/workflows/ci.yml`

It now validates every push and pull request with:

1. `ruff check .`
2. `pytest`
3. `docker build --tag rs3-tracker-ci .`

## Review plan status

Recently completed from `REVIEW.md`:

- Migration framework in `db.py` and schema migration execution
- Quest field migration (`quests_started`, `quests_complete`, `quests_not_started`)
- Collector quest-field mapping update
- Secret Manager deployment wiring in `cloudbuild.yaml`

Next recommended implementation block:

1. Break down `app.py` into `config`, routes, repositories, and services while preserving behavior.
2. Move collector scheduling out of web app lifespan (Cloud Scheduler or Cloud Run Job).
3. Add admin POST CSRF protection and lightweight admin rate limiting.
``````

#### log.py
```python
"""
Logging configuration for rs3-tracker.

Import and call configure_logging() once at startup (done in app lifespan).
All other modules should obtain their logger via get_logger(__name__).

Log level is controlled by the LOG_LEVEL environment variable (default: INFO).
"""

import logging
import os

_CONFIGURED = False

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging() -> None:
    """Configure the root logger. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    # Silence overly chatty third-party loggers at WARNING unless debug is on.
    if level > logging.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger. Call as get_logger(__name__)."""
    return logging.getLogger(name)
```

#### Dockerfile
```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app.py collector.py config.py db.py log.py skills.py utils.py web.py ./
COPY services ./services
COPY routes ./routes
RUN uv pip install --system .

COPY static ./static
COPY templates ./templates

ENV DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### db.py
```python
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
```

#### config.py
```python
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
```

#### collector.py
```python
import asyncio
import hashlib
import sqlite3

import httpx

from config import RS3_USERNAME
from db import get_conn, init_db
from log import get_logger
from skills import SKILL_NAMES

logger = get_logger(__name__)

USERNAME = RS3_USERNAME
API_URL = f"https://apps.runescape.com/runemetrics/profile/profile?user={USERNAME}&activities=20"

# Global lock to prevent concurrent snapshot collections (e.g., background loop vs manual trigger)
_collection_lock = asyncio.Lock()


def hash_activity(text, date, details):
    return hashlib.sha256(f"{text}|{date}|{details or ''}".encode()).hexdigest()


def legacy_hash_activity(text, date):
    return hashlib.sha256(f"{text}|{date}".encode()).hexdigest()


def to_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return default
        try:
            return int(cleaned)
        except ValueError:
            return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def _fetch_runemetrics_data(client: httpx.AsyncClient, retries: int = 3):
    """Fetch data with exponential backoff for resilience."""
    for attempt in range(retries):
        try:
            r = await client.get(API_URL, timeout=15.0)
            r.raise_for_status()
            return r.json()
        except httpx.RequestError as e:
            logger.warning(
                "RuneMetrics API request failed (attempt %d/%d): %s",
                attempt + 1,
                retries,
                e,
            )
            if attempt == retries - 1:
                logger.error("All retries failed for RuneMetrics API.")
                return None
            await asyncio.sleep(2**attempt)  # 1s, 2s, 4s...
    return None


async def collect_snapshot():
    """Asynchronous collector that safely blocks concurrent runs."""
    async with _collection_lock:
        async with httpx.AsyncClient() as client:
            data = await _fetch_runemetrics_data(client)

        if not data:
            return

        if "error" in data or "skillvalues" not in data:
            logger.warning(
                "Invalid RuneMetrics response for user %s — profile may be private",
                USERNAME,
            )
            return

        # Execute DB inserts synchronously (SQLite handles this instantly with WAL mode)
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute(
                "INSERT OR IGNORE INTO players (username) VALUES (?)", (USERNAME,)
            )
            cur.execute("SELECT id FROM players WHERE username=?", (USERNAME,))
            player_id = cur.fetchone()["id"]

            rank = to_int(data.get("rank"), 0)
            total_xp = to_int(data.get("totalxp"), 0)
            total_level = to_int(data.get("totalskill"), 0)
            combat_level = to_int(data.get("combatlevel"), 0)
            quests_started = to_int(data.get("questsstarted"), 0)
            quests_complete = to_int(data.get("questscomplete"), 0)
            quests_not_started = to_int(data.get("questsnotstarted"), 0)

            cur.execute(
                """
                INSERT INTO snapshots (
                    player_id,
                    total_xp,
                    total_level,
                    overall_rank,
                    combat_level,
                    quests_started,
                    quests_complete,
                    quests_not_started
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player_id,
                    total_xp,
                    total_level,
                    rank,
                    combat_level,
                    quests_started,
                    quests_complete,
                    quests_not_started,
                ),
            )
            snapshot_id = cur.lastrowid

            skills_data = []
            for skill in data["skillvalues"]:
                skill_name = SKILL_NAMES.get(skill["id"], f"Unknown-{skill['id']}")
                skills_data.append(
                    (
                        snapshot_id,
                        skill_name,
                        to_int(skill.get("level"), 0),
                        to_int(skill.get("xp"), 0),
                        to_int(skill.get("rank"), 0),
                    )
                )

            cur.executemany(
                "INSERT INTO skills (snapshot_id, skill, level, xp, rank) VALUES (?, ?, ?, ?, ?)",
                skills_data,
            )

            for act in data.get("activities", []):
                details = act.get("details")
                h = hash_activity(act["text"], act["date"], details)
                legacy_h = legacy_hash_activity(act["text"], act["date"])
                cur.execute(
                    "SELECT 1 FROM activities WHERE hash IN (?, ?) LIMIT 1",
                    (h, legacy_h),
                )
                if cur.fetchone():
                    continue
                try:
                    cur.execute(
                        "INSERT INTO activities (snapshot_id, text, date, details, hash) VALUES (?, ?, ?, ?, ?)",
                        (snapshot_id, act["text"], act["date"], details, h),
                    )
                except sqlite3.IntegrityError:
                    pass  # Duplicate activity, ignore

            conn.commit()

        logger.info(
            "Snapshot collected for %s — total XP: %s",
            USERNAME,
            total_xp,
        )


if __name__ == "__main__":
    init_db()
    asyncio.run(collect_snapshot())
```

#### cloudbuild.yaml
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      [
        'build',
        '-t',
        '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_IMAGE}:$COMMIT_SHA',
        '.'
      ]

  - name: 'gcr.io/cloud-builders/docker'
    args:
      [
        'push',
        '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_IMAGE}:$COMMIT_SHA'
      ]

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: bash
    args:
      - -ceu
      - |
        IMAGE_URI="${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_IMAGE}:$COMMIT_SHA"

        deploy_args=(
          run deploy "${_SERVICE}"
          --image "$${IMAGE_URI}"
          --region "${_REGION}"
          --platform managed
          --allow-unauthenticated
        )

        if [[ -n "${_ADMIN_USERNAME_SECRET}" && -n "${_ADMIN_PASSWORD_SECRET}" ]]; then
          deploy_args+=(
            --set-secrets
            "ADMIN_USERNAME=${_ADMIN_USERNAME_SECRET}:latest,ADMIN_PASSWORD=${_ADMIN_PASSWORD_SECRET}:latest"
          )
          echo "Deploying with Secret Manager admin credentials."
        else
          echo "Deploying without Secret Manager substitutions."
        fi

        gcloud "$${deploy_args[@]}"

substitutions:
  _REGION: europe-north1
  _REPOSITORY: rs3-tracker
  _IMAGE: rs3-tracker
  _SERVICE: rs3-tracker
  _ADMIN_USERNAME_SECRET: 'rs3-admin-username'
  _ADMIN_PASSWORD_SECRET: 'rs3-admin-password'

options:
  logging: CLOUD_LOGGING_ONLY
```

#### app.py
```python
"""
Application composition root.

This file's only jobs:
  1. Create the FastAPI app and configure its lifespan.
  2. Mount static files.
  3. Include routers from routes/.

All logic lives in services/, routes/, and supporting modules.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from collector import collect_snapshot
from db import init_db
from log import configure_logging, get_logger
from routes.admin import router as admin_router
from routes.public import router as public_router

logger = get_logger(__name__)


async def _background_loop() -> None:
    while True:
        try:
            await collect_snapshot()  # Changed to await directly
        except Exception:
            logger.exception("Collector error in background loop")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    asyncio.create_task(_background_loop())
    yield


app = FastAPI(lifespan=lifespan, title="RS3 Tracker")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(public_router)
app.include_router(admin_router)
```

#### .dockerignore
```text
.git
.gitignore
.github
.venv
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
data/
*.db
*.sqlite
*.sqlite3
*.log
.env
.env.*
REVIEW.md
```

#### static/style.css
```css
:root {
    --bg-color: #15171a;
    --panel-bg: #1d2024;
    --text-main: #e6e8eb;
    --text-muted: #9aa1ab;
    --accent: #8da0b6;
    --success: #75bc7a;
    --danger: #dc8f81;
    --border: #31353c;
    --surface-2: #121519;
}

body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg-color);
    color: var(--text-main);
    margin: 0;
    padding: 20px;
    line-height: 1.5;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
}

h1,
h2 {
    margin: 0 0 16px 0;
    font-weight: 600;
}

.stats-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(220px, 1fr) minmax(280px, 1fr);
    gap: 16px;
    margin-bottom: 32px;
}

.stat-card {
    background: var(--panel-bg);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
}

.stat-card-wide {
    min-width: 0;
}

.stat-title {
    color: var(--text-muted);
    font-size: 0.875rem;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.stat-title-main {
    color: var(--text-main);
    font-size: 1.3rem;
    text-transform: none;
    font-weight: 700;
    margin-bottom: 12px;
}

.stat-gain {
    font-size: 0.875rem;
    color: var(--success);
    margin-top: 4px;
}

.summary-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    align-content: start;
}

.summary-metric {
    padding: 10px 0;
    border-top: 1px solid var(--border);
}

.summary-label {
    color: var(--text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.summary-value {
    margin-top: 2px;
    font-weight: 700;
    font-size: 1.125rem;
}

.active-skills-list {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex: 1;
    justify-content: space-between;
}

.active-skill-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.875rem;
}

.active-skills-empty {
    margin-top: auto;
    padding-top: 10px;
}

.nearest-level-list {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    flex: 1;
    justify-content: space-between;
}

.nearest-level-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
}

.nearest-level-skill {
    font-weight: 700;
    font-size: 0.95rem;
}

.nearest-level-xp {
    font-weight: 700;
    color: var(--accent);
    font-size: 0.95rem;
    text-align: right;
}

.main-content {
    display: grid;
    grid-template-columns: 1fr 350px;
    gap: 24px;
}

.left-column {
    display: flex;
    flex-direction: column;
}

.side-panel {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

@media (max-width: 1024px) {
    .stats-grid {
        grid-template-columns: 1fr 1fr;
    }

    .summary-metrics {
        grid-template-columns: 1fr;
    }

    .main-content {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 760px) {
    .stats-grid {
        grid-template-columns: 1fr;
    }

}

.panel {
    background: var(--panel-bg);
    padding: 24px;
    border-radius: 12px;
    border: 1px solid var(--border);
}

.tab-panel {
    min-height: 640px;
}

.tab-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 16px;
}

.tab-buttons {
    display: flex;
    gap: 8px;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

.skills-heading {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
}

.skills-gain-indicator {
    color: var(--text-muted);
    font-size: 0.78rem;
}

.skills-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
}

.skill-card {
    --skill-color: var(--accent);
    background: rgba(18, 21, 25, 0.78);
    border: 1px solid var(--border);
    border-left: 3px solid var(--skill-color);
    border-radius: 8px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.2s;
}

.skill-card:hover {
    border-color: var(--skill-color);
    transform: translateY(-2px);
}

.skill-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
}

.skill-name {
    font-weight: 600;
}

.skill-level {
    color: var(--skill-color);
    font-weight: 700;
}

.skill-details {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 8px;
}

.xp-gain-positive {
    color: var(--success);
}

.xp-gain-negative {
    color: var(--danger);
}

.progress-bg {
    background: var(--surface-2);
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
}

.progress-fill {
    background: var(--skill-color);
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease-out;
}

.activities-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.activity-item {
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 10px;
    align-items: start;
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-date {
    font-size: 0.72rem;
    color: var(--text-muted);
    white-space: nowrap;
    margin-top: 1px;
}

.activity-text {
    font-size: 0.82rem;
}

.feed-layout {
    display: grid;
    grid-template-columns: 180px minmax(0, 1fr);
    gap: 18px;
}

.feed-rail {
    position: sticky;
    top: 14px;
    align-self: start;
}

.feed-rail-link {
    display: block;
    width: 100%;
    background: transparent;
    border-top: none;
    border-right: none;
    border-bottom: none;
    color: var(--text-muted);
    border-left: 2px solid var(--border);
    padding: 6px 8px;
    margin-bottom: 3px;
    font-size: 0.82rem;
    text-align: left;
    font: inherit;
    transition: color 0.15s ease, border-color 0.15s ease;
    cursor: pointer;
}

.feed-rail-link:hover {
    color: var(--text-main);
    border-color: var(--accent);
}

.feed-stream {
    display: grid;
    gap: 16px;
    align-content: start;
}

.feed-day-group {
    border-top: 1px solid var(--border);
    padding-top: 12px;
}

.feed-day-title {
    margin: 0 0 10px 0;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.76rem;
}

.feed-card-flow {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 8px;
}

.feed-card {
    --card-accent: var(--accent);
    --card-icon-url: url('/static/icons_64/activity.png');
    display: grid;
    grid-template-columns: 46px 1fr;
    gap: 8px;
    width: fit-content;
    max-width: min(100%, 52ch);
    border: 1px solid var(--border);
    border-radius: 10px;
    background: rgba(18, 21, 25, 0.7);
}

.feed-card-rail {
    width: 54px;
    aspect-ratio: 1 / 1;
    align-self: center;
    position: relative;
    border-radius: 10px;
    overflow: hidden;
    -webkit-mask-image: linear-gradient(to right, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0) 100%);
    mask-image: linear-gradient(to right, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0) 100%);
}

.feed-card-rail::before {
    content: "";
    position: absolute;
    inset: -6px;
    background-image: var(--card-icon-url);
    background-repeat: no-repeat;
    background-position: center;
    background-size: 80% 80%;
    transform: rotate(-8deg);
    opacity: 0.88;
    filter: saturate(0.85) contrast(0.95);
}

.feed-card-body {
    padding: 8px 10px 8px 2px;
    min-width: 0;
}

.feed-card-title {
    margin: 0;
    font-size: 0.84rem;
    font-weight: 600;
    line-height: 1.3;
}

.feed-card-date {
    margin-top: 4px;
    color: var(--text-muted);
    font-size: 0.7rem;
}

.feed-type-level {
    --card-accent: #69a8ff;
}

.feed-type-quest {
    --card-accent: #9ecb67;
}

.feed-type-kill {
    --card-accent: #d78070;
}

.feed-type-loot {
    --card-accent: #d1b366;
}

.feed-type-achievement {
    --card-accent: #95b999;
}

.feed-type-clue {
    --card-accent: #a48ad8;
}

.feed-type-unlock {
    --card-accent: #6ec2bb;
}

/* Modal */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-overlay.active {
    display: flex;
}

.modal-content {
    --modal-accent: var(--accent);
    background: var(--panel-bg);
    padding: 24px;
    border-radius: 12px;
    width: 90%;
    max-width: 800px;
    border: 1px solid var(--border);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.skill-gain-summary {
    font-size: 0.88rem;
    color: var(--text-muted);
    margin: -2px 0 10px 0;
}

.close-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1.5rem;
    cursor: pointer;
}

.close-btn:hover {
    color: var(--text-main);
}

.chart-controls {
    display: flex;
    gap: 8px;
    margin-top: 16px;
    justify-content: center;
}

.tf-btn {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    font-weight: 600;
}

.tf-btn:hover,
.tf-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #0f1217;
}

.modal-content .tf-btn:hover,
.modal-content .tf-btn.active {
    background: var(--modal-accent);
    border-color: var(--modal-accent);
    color: var(--text-main);
}

.admin-link-btn {
    text-decoration: none;
}

.admin-alert {
    margin-bottom: 16px;
    padding: 12px 16px;
}

.admin-alert-success {
    border-color: rgba(117, 188, 122, 0.55);
    color: var(--success);
}

.admin-alert-error {
    border-color: rgba(176, 77, 63, 0.65);
    color: #dc8f81;
}

.admin-overview-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.admin-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.admin-sql-input {
    width: 100%;
    min-height: 180px;
    resize: vertical;
    box-sizing: border-box;
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-main);
    border-radius: 8px;
    padding: 12px;
    font: 0.9rem/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.admin-table {
    width: 100%;
    border-collapse: collapse;
}

.admin-table th,
.admin-table td {
    border: 1px solid var(--border);
    text-align: left;
    padding: 8px;
    vertical-align: top;
    font-size: 0.85rem;
}

.admin-table th {
    background: var(--surface-2);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.74rem;
}

.admin-results-wrap {
    overflow-x: auto;
}

.admin-mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.85rem;
    word-break: break-all;
}

@media (max-width: 760px) {
    .skills-heading {
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
    }

    .tab-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
    }

    .tab-buttons {
        width: 100%;
    }

    .tab-buttons .tf-btn {
        flex: 1;
    }

    .feed-layout {
        grid-template-columns: 1fr;
    }

    .feed-rail {
        position: static;
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 8px;
    }

    .feed-rail-link {
        display: inline-block;
        margin-right: 6px;
        margin-bottom: 0;
        width: auto;
    }

    .feed-card-flow {
        display: flex;
        flex-direction: column;
        gap: 7px;
    }

    .feed-card {
        grid-template-columns: 42px 1fr;
        width: 100%;
        max-width: 100%;
    }

    .feed-card-rail {
        width: 42px;
    }

    .activity-item {
        grid-template-columns: 1fr;
        gap: 2px;
    }

    .admin-overview-grid {
        grid-template-columns: 1fr;
    }
}
```

#### tests/test_dummy.py
```python
def test_dummy():
    assert 1 == 1
```

#### templates/index.html
```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.player_name if data else 'RS3 Tracker' }} - RS3 Tracker</title>
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/moment"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment"></script>
    <link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16x16.png">
    <link rel="manifest" href="/static/site.webmanifest">
</head>

<body>
    <div class="container">
        <header>
            <div>
                <h1>RS3 Tracker</h1>
                <div style="color: var(--text-muted)">
                    Last updated: <span id="lastUpdated">{{ data.latest.timestamp if data else 'Never' }}</span>
                </div>
            </div>
            <div style="display: flex; gap: 10px;">
                <a href="/admin" class="tf-btn admin-link-btn">Admin</a>
                <button id="updateBtn" class="tf-btn">Update Now</button>
            </div>
        </header>

        {% if data %}
        <div class="stats-grid">
            <div class="stat-card stat-card-wide">
                <div class="stat-title stat-title-main">{{ data.player_name }}</div>
                <div class="summary-metrics">
                    <div class="summary-metric">
                        <div class="summary-label">Total XP</div>
                        <div class="summary-value">{{ data.latest.total_xp_display }}</div>
                    </div>
                    <div class="summary-metric">
                        <div class="summary-label">Total Level</div>
                        <div class="summary-value">{{ "{:,}".format(data.latest.total_level) }}</div>
                    </div>
                    <div class="summary-metric">
                        <div class="summary-label">Overall Rank</div>
                        <div class="summary-value">{{ "{:,}".format(data.latest.overall_rank) }}</div>
                    </div>
                    <div class="summary-metric">
                        <div class="summary-label">Combat</div>
                        <div class="summary-value">{{ data.latest.combat_level }}</div>
                    </div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Today's Biggest Gainers</div>
                {% if data.top_gainers_today %}
                <div class="active-skills-list">
                    {% for s in data.top_gainers_today %}
                    <div class="active-skill-row">
                        <span>{{ loop.index }}. {{ s.skill }}</span>
                        <span class="xp-gain-positive">+{{ s.xp_gain_display }}</span>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="summary-label active-skills-empty">No gains today</div>
                {% endif %}
            </div>
            <div class="stat-card">
                <div class="stat-title">Today Highlights</div>
                <div class="active-skills-list">
                    <div class="active-skill-row">
                        <span>XP Gained Today</span>
                        <span class="xp-gain-positive">+{{ data.today_highlights.xp_today_display }}</span>
                    </div>
                    <div class="active-skill-row">
                        <span>Levels Gained</span>
                        <span class="{{ 'xp-gain-positive' if data.today_highlights.levels_gained_today > 0 else '' }}">
                            {{ '+' if data.today_highlights.levels_gained_today > 0 else '' }}{{ "{:,}".format(data.today_highlights.levels_gained_today) }}
                        </span>
                    </div>
                    <div class="active-skill-row">
                        <span>Quests Finished</span>
                        <span class="{{ 'xp-gain-positive' if data.today_highlights.quests_finished_today > 0 else '' }}">
                            {{ '+' if data.today_highlights.quests_finished_today > 0 else '' }}{{ "{:,}".format(data.today_highlights.quests_finished_today) }}
                        </span>
                    </div>
                    <div class="active-skill-row">
                        <span>Rank Change</span>
                        <span class="{{ data.today_highlights.rank_delta_today_class }}">
                            {{ data.today_highlights.rank_delta_today_display }}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <div class="main-content">
            <div class="left-column">
                <div class="panel tab-panel">
                    <div class="tab-header">
                        <div class="tab-buttons">
                            <button class="tf-btn tab-btn active" data-tab="skills">Skills</button>
                            <button class="tf-btn tab-btn" data-tab="feed">Activity Feed</button>
                        </div>
                    </div>

                    <div class="tab-content active" data-tab-content="skills">
                        <div class="skills-grid">
                            {% for s in data.skills %}
                            <div class="skill-card" data-skill="{{ s.skill }}" style="--skill-color: {{ s.color }};">
                                <div class="skill-header">
                                    <span class="skill-name">{{ s.skill }}</span>
                                    <span class="skill-level">{{ s.level }}</span>
                                </div>
                                <div class="skill-details">
                                    <span>{{ s.xp_display }} XP</span>
                                    {% if s.xp_gain > 0 %}
                                    <span class="xp-gain-positive">Today +{{ s.xp_gain_display }}</span>
                                    {% endif %}
                                </div>
                                <div class="progress-bg">
                                    <div class="progress-fill" style="width: {{ s.progress * 100 }}%"></div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>

                    <div class="tab-content" data-tab-content="feed">
                        <div class="feed-layout">
                            <aside class="feed-rail">
                                <div id="feedRailNav"></div>
                            </aside>
                            <div class="feed-stream" id="feedStream"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="side-panel">
                <div class="panel" style="margin-bottom: 24px;">
                    <h2>Total XP (30 Days)</h2>
                    <canvas id="totalXpChart" height="200"></canvas>
                </div>
                <div class="panel closest-level-card">
                    <h2>Closest Level-Ups</h2>
                    {% if data.closest_levels %}
                    <div class="nearest-level-list">
                        {% for s in data.closest_levels %}
                        <div class="nearest-level-row">
                            <div>
                                <div class="nearest-level-skill">{{ loop.index }}. {{ s.skill }}</div>
                                <div class="summary-label">To level {{ s.target_level }}</div>
                            </div>
                            <div class="nearest-level-xp">{{ s.xp_to_next_display }} XP</div>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div class="summary-label active-skills-empty">All tracked skills are maxed</div>
                    {% endif %}
                </div>
            </div>
        </div>
        {% else %}
        <div class="panel">
            <p>No data collected yet. Click "Update Now" to run the collector.</p>
        </div>
        {% endif %}
    </div>

    <!-- Skill History Modal -->
    <div class="modal-overlay" id="skillModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalSkillTitle">Skill History</h2>
                <button class="close-btn" id="closeModal">&times;</button>
            </div>
            <div id="skillGainSummary" class="skill-gain-summary"></div>
            <canvas id="skillChart" height="100"></canvas>
            <div id="skillNoGainsMessage" style="display:none; color: var(--text-muted); margin-top: 12px;">
                No gains in the selected range yet.
            </div>
            <div class="chart-controls">
                <button class="tf-btn active" data-period="day">1 day</button>
                <button class="tf-btn" data-period="week">1 week</button>
                <button class="tf-btn" data-period="month">1 month</button>
                <button class="tf-btn" data-period="year">1 year</button>
                <button class="tf-btn" data-period="all">all</button>
            </div>
        </div>
    </div>

    <script>
        const numberFmt = new Intl.NumberFormat();
        const cssVars = getComputedStyle(document.documentElement);
        const chartAccent = cssVars.getPropertyValue('--accent').trim() || '#8da0b6';
        const chartMuted = cssVars.getPropertyValue('--text-muted').trim() || '#9aa1ab';
        const chartGrid = cssVars.getPropertyValue('--border').trim() || '#31353c';
        const hexToRgba = (hex, alpha) => {
            if (!hex || !hex.startsWith('#')) return `rgba(141, 160, 182, ${alpha})`;
            const full = hex.length === 4
                ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`
                : hex;
            const int = parseInt(full.slice(1), 16);
            const r = (int >> 16) & 255;
            const g = (int >> 8) & 255;
            const b = int & 255;
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        };
        const formatXpNumber = (value) =>
            value == null || Number.isNaN(Number(value)) ? '-' : numberFmt.format(Math.round(Number(value)));
        const previousNonNull = (series, index) => {
            for (let i = index - 1; i >= 0; i--) {
                if (series[i] != null) return Number(series[i]);
            }
            return null;
        };
        const formatDelta = (current, previous) => {
            if (current == null || previous == null) return 'n/a';
            const delta = Number(current) - Number(previous);
            const sign = delta > 0 ? '+' : '';
            return `${sign}${numberFmt.format(Math.round(delta))}`;
        };
        // Format Local Time
        const lu = document.getElementById('lastUpdated');
        if (lu && lu.textContent !== 'Never') {
            lu.textContent = new Date(lu.textContent).toLocaleString();
        }

        // Manual Update Button
        document.getElementById('updateBtn').addEventListener('click', async (e) => {
            e.target.disabled = true; e.target.textContent = 'Updating...';
            await fetch('/api/update', { method: 'POST' });
            location.reload();
        });

        {% if data %}
        const activitiesData = {{ data.activities | tojson }};

        function formatFeedDayLabel(dayDate, now) {
            const dayStart = new Date(dayDate.getFullYear(), dayDate.getMonth(), dayDate.getDate());
            const nowStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const diffDays = Math.round((nowStart - dayStart) / 86400000);
            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            return dayDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        }

        function groupActivitiesByDay(items) {
            const groups = new Map();
            items.forEach((activity) => {
                const dt = activity.date_iso ? new Date(activity.date_iso) : null;
                if (dt && !Number.isNaN(dt.valueOf())) {
                    const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
                    if (!groups.has(key)) groups.set(key, { dt, items: [] });
                    groups.get(key).items.push(activity);
                    return;
                }
                if (!groups.has('Unknown')) groups.set('Unknown', { dt: null, items: [] });
                groups.get('Unknown').items.push(activity);
            });
            return [...groups.entries()].map(([key, value]) => ({
                key,
                dt: value.dt,
                items: value.items
            }));
        }

        function renderActivityFeed(items) {
            const rail = document.getElementById('feedRailNav');
            const stream = document.getElementById('feedStream');
            if (!rail || !stream) return;

            rail.innerHTML = '';
            stream.innerHTML = '';

            const groups = groupActivitiesByDay(items);
            const now = new Date();
            const typeCounts = new Map();

            if (!groups.length) {
                const empty = document.createElement('div');
                empty.className = 'summary-label';
                empty.textContent = 'No activities yet.';
                stream.appendChild(empty);
                return;
            }

            groups.forEach((group) => {
                const section = document.createElement('section');
                section.className = 'feed-day-group';

                const railBtn = document.createElement('button');
                railBtn.type = 'button';
                railBtn.className = 'feed-rail-link';
                railBtn.textContent = group.dt ? formatFeedDayLabel(group.dt, now) : 'Unknown Date';
                railBtn.addEventListener('click', () => {
                    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
                rail.appendChild(railBtn);

                const dayTitle = document.createElement('h3');
                dayTitle.className = 'feed-day-title';
                dayTitle.textContent = group.dt ? formatFeedDayLabel(group.dt, now) : 'Unknown Date';
                section.appendChild(dayTitle);

                const cardFlow = document.createElement('div');
                cardFlow.className = 'feed-card-flow';

                group.items.forEach((activity) => {
                    const card = document.createElement('article');
                    card.className = `feed-card feed-type-${activity.type_key || 'activity'}`;
                    if (activity.color) card.style.setProperty('--card-accent', activity.color);

                    const rail = document.createElement('div');
                    rail.className = 'feed-card-rail';
                    const iconPath = activity.skill
                        ? `/static/skills_64/${activity.skill.toLowerCase()}.png`
                        : `/static/icons_64/${activity.type_key || 'activity'}.png`;
                    rail.style.setProperty('--card-icon-url', `url("${iconPath}")`);

                    const body = document.createElement('div');
                    body.className = 'feed-card-body';
                    const title = document.createElement('h4');
                    title.className = 'feed-card-title';
                    title.textContent = activity.details ?? activity.text;

                    const date = document.createElement('div');
                    date.className = 'feed-card-date';
                    if (activity.date_iso) {
                        const dt = new Date(activity.date_iso);
                        date.textContent = Number.isNaN(dt.valueOf())
                            ? activity.date
                            : dt.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
                    } else {
                        date.textContent = activity.date || '';
                    }

                    body.appendChild(title);
                    body.appendChild(date);
                    card.appendChild(rail);
                    card.appendChild(body);
                    cardFlow.appendChild(card);

                    const typeLabel = activity.type_label || 'Activity';
                    typeCounts.set(typeLabel, (typeCounts.get(typeLabel) || 0) + 1);
                });

                section.appendChild(cardFlow);
                stream.appendChild(section);
            });

            [...typeCounts.entries()]
                .sort((a, b) => b[1] - a[1])
                .forEach(([label, count]) => {
                    const row = document.createElement('div');
                    row.className = 'active-skill-row';
                    const l = document.createElement('span');
                    l.textContent = label;
                    const c = document.createElement('span');
                    c.textContent = numberFmt.format(count);
                    row.appendChild(l);
                    row.appendChild(c);
                });
        }

        function activateTab(tab) {
            document.querySelectorAll('.tab-btn').forEach((btn) => {
                btn.classList.toggle('active', btn.dataset.tab === tab);
            });
            document.querySelectorAll('.tab-content').forEach((content) => {
                content.classList.toggle('active', content.dataset.tabContent === tab);
            });
        }

        document.querySelectorAll('.tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => activateTab(btn.dataset.tab));
        });

        renderActivityFeed(activitiesData);
        activateTab('skills');

        // Static total XP chart (30 days)
        new Chart(document.getElementById('totalXpChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: {{ data.timestamps | tojson }},
            datasets: [{
                label: 'Total XP', data: {{ data.xp_history | tojson }},
            borderColor: chartAccent, backgroundColor: hexToRgba(chartAccent, 0.15),
            borderWidth: 2, fill: true, tension: 0.4, pointRadius: 0
                }]
            },
            options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `Total XP: ${formatXpNumber(ctx.parsed.y)}`,
                        afterLabel: (ctx) => {
                            const prev = previousNonNull(ctx.dataset.data, ctx.dataIndex);
                            return `Delta: ${formatDelta(ctx.parsed.y, prev)}`;
                        }
                    }
                }
            },
            scales: {
                x: { type: 'time', time: { tooltipFormat: 'll HH:mm' }, ticks: { color: chartMuted }, grid: { color: chartGrid } },
                y: { ticks: { color: chartMuted, callback: val => val.toLocaleString() }, grid: { color: chartGrid } }
            }
        }
        });

        // Skill modal chart
        const modal = document.getElementById('skillModal');
        const modalContent = modal.querySelector('.modal-content');
        const noGains = document.getElementById('skillNoGainsMessage');
        const gainSummary = document.getElementById('skillGainSummary');
        let currentSkill = '';
        let currentSkillColor = chartAccent;
        let skillChartInstance = null;
        const periodLabel = (period) => {
            if (period === 'day') return 'past day';
            if (period === 'week') return 'past week';
            if (period === 'month') return 'current month';
            if (period === 'year') return 'past year';
            return 'selected range';
        };
        const calculateRangeGain = (series) => {
            const values = (series || []).filter(v => v != null).map(Number);
            if (!values.length) return null;
            return Math.max(0, values[values.length - 1] - values[0]);
        };

        document.querySelectorAll('.skill-card').forEach(card => {
            card.addEventListener('click', () => {
                currentSkill = card.dataset.skill;
                currentSkillColor = getComputedStyle(card).getPropertyValue('--skill-color').trim() || chartAccent;
                modalContent.style.setProperty('--modal-accent', currentSkillColor);
                document.getElementById('modalSkillTitle').textContent = `${currentSkill} History`;
                modal.classList.add('active');

                document.querySelectorAll('#skillModal .chart-controls .tf-btn').forEach(b => b.classList.remove('active'));
                document.querySelector('#skillModal .chart-controls .tf-btn[data-period="day"]').classList.add('active');
                loadSkillData(currentSkill, 'day');
            });
        });

        document.getElementById('closeModal').addEventListener('click', () => modal.classList.remove('active'));
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('active'); });

        document.querySelectorAll('#skillModal .chart-controls .tf-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('#skillModal .chart-controls .tf-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                loadSkillData(currentSkill, e.target.dataset.period);
            });
        });

        async function loadSkillData(skill, period) {
            const res = await fetch(`/api/chart/${encodeURIComponent(skill)}/${period}`);
            const chartData = await res.json();
            const totalGain = calculateRangeGain(chartData.totals);
            const range = periodLabel(period);

            if (skillChartInstance) {
                skillChartInstance.destroy();
                skillChartInstance = null;
            }

            if (!chartData.has_gains) {
                noGains.style.display = 'block';
                gainSummary.textContent = `Gained in ${range}: n/a`;
                return;
            }

            noGains.style.display = 'none';
            gainSummary.textContent = `Gained in ${range}: ${formatXpNumber(totalGain)} XP`;
            const timeUnit = period === 'day' ? 'hour' : 'day';
            const tooltipFormat = period === 'day' ? 'll HH:mm' : 'll';
            const pointRadius = chartData.labels.length > 180 ? 0 : (chartData.labels.length > 60 ? 1.5 : 3);

            skillChartInstance = new Chart(document.getElementById('skillChart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: `${skill} XP`,
                        data: chartData.totals,
                        borderColor: currentSkillColor,
                        backgroundColor: hexToRgba(currentSkillColor, 0.15),
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: pointRadius
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.dataset.label}: ${formatXpNumber(ctx.parsed.y)}`,
                                afterLabel: (ctx) => {
                                    const prev = previousNonNull(ctx.dataset.data, ctx.dataIndex);
                                    return `Delta: ${formatDelta(ctx.parsed.y, prev)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: timeUnit,
                                tooltipFormat: tooltipFormat,
                                displayFormats: {
                                    hour: 'HH:mm',
                                    day: 'MMM D'
                                }
                            },
                            ticks: { color: chartMuted },
                            grid: { color: chartGrid }
                        },
                        y: { ticks: { color: chartMuted, callback: val => val.toLocaleString() }, grid: { color: chartGrid } }
                    }
                }
            });
        }
        {% endif %}
    </script>
</body>

</html>
```

#### templates/admin.html
```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - RS3 Tracker</title>
    <link rel="stylesheet" href="/static/style.css">
</head>

<body>
    <div class="container">
        <header>
            <div>
                <h1>Admin</h1>
                <div style="color: var(--text-muted)">Protected maintenance interface</div>
            </div>
            <a href="/" class="tf-btn admin-link-btn">Back to Dashboard</a>
        </header>

        {% if message %}
        <div class="panel admin-alert admin-alert-success">{{ message }}</div>
        {% endif %}
        {% if sql_error %}
        <div class="panel admin-alert admin-alert-error">{{ sql_error }}</div>
        {% endif %}

        <div class="panel" style="margin-bottom: 20px;">
            <h2>Database Overview</h2>
            <div class="admin-overview-grid">
                <div class="summary-cell">
                    <div class="summary-label">DB Path</div>
                    <div class="summary-value admin-mono">{{ overview.db_path }}</div>
                </div>
                <div class="summary-cell">
                    <div class="summary-label">DB Size</div>
                    <div class="summary-value">{{ overview.db_size_mb }} MB</div>
                </div>
                <div class="summary-cell">
                    <div class="summary-label">Latest Snapshot</div>
                    <div class="summary-value">{{ overview.latest_snapshot_ts or "No data yet" }}</div>
                </div>
            </div>
            <table class="admin-table" style="margin-top: 14px;">
                <thead>
                    <tr>
                        <th>Table</th>
                        <th>Rows</th>
                    </tr>
                </thead>
                <tbody>
                    {% for t in overview.table_counts %}
                    <tr>
                        <td>{{ t.name }}</td>
                        <td>{{ "{:,}".format(t.count) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="panel" style="margin-bottom: 20px;">
            <h2>Maintenance</h2>
            <div class="admin-actions">
                <form method="post" action="/admin/maintenance/update">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button type="submit" class="tf-btn">Collect Snapshot Now</button>
                </form>
                <form method="post" action="/admin/maintenance/checkpoint">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button type="submit" class="tf-btn">Run WAL Checkpoint</button>
                </form>
                <form method="post" action="/admin/maintenance/vacuum">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button type="submit" class="tf-btn">Run VACUUM</button>
                </form>
            </div>
        </div>

        <div class="panel">
            <h2>SQL Console</h2>
            <div class="summary-label" style="margin-bottom: 10px;">
                Executes one SQL statement at a time. Query results are capped to 200 rows.
            </div>
            <form method="post" action="/admin/sql">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <textarea class="admin-sql-input" name="sql"
                    placeholder="SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 10;">{{ sql }}</textarea>
                <div style="margin-top: 10px;">
                    <button type="submit" class="tf-btn">Run SQL</button>
                </div>
            </form>
            {% if sql_rowcount is not none %}
            <div class="summary-label" style="margin-top: 12px;">Rows affected: {{ sql_rowcount }}</div>
            {% endif %}
            {% if sql_columns and sql_rows %}
            <div class="admin-results-wrap">
                <table class="admin-table" style="margin-top: 16px;">
                    <thead>
                        <tr>
                            {% for col in sql_columns %}
                            <th>{{ col }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in sql_rows %}
                        <tr>
                            {% for col in sql_columns %}
                            <td>{{ row[col] }}</td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
        </div>
    </div>
</body>

</html>
```

#### services/dashboard.py
```python
"""
Dashboard assembly service.

Pulls data from the DB and returns a plain dict ready for the template.
No FastAPI / HTTP concerns here.
"""

import re
from datetime import datetime, timedelta, timezone

from db import get_conn
from services.charts import (
    format_skill_xp,
    format_total_xp,
    get_window_baseline,
    parse_activity_ts,
    scale_total_xp,
)
from skills import ACTIVITY_TYPE_META, RS3_ORDER, SKILL_COLORS
from utils import calculate_progress, xp_to_next_level

# ---------------------------------------------------------------------------
# Activity helpers
# ---------------------------------------------------------------------------


def detect_activity_skill(text: str | None) -> str | None:
    lowered = (text or "").lower()
    for skill in RS3_ORDER:
        if re.search(rf"\b{re.escape(skill.lower())}\b", lowered):
            return skill
    return None


def classify_activity_meta(text: str | None, details: str | None = None) -> dict:
    combined = " ".join(part for part in (details, text) if part)
    lowered = combined.lower()

    type_key = "activity"
    if "quest" in lowered:
        type_key = "quest"
    elif "clue" in lowered or "treasure trail" in lowered:
        type_key = "clue"
    elif "levelled" in lowered or "leveled" in lowered or "advanced" in lowered:
        type_key = "level"
    elif "killed" in lowered or "defeated" in lowered or "slain" in lowered:
        type_key = "kill"
    elif "drop" in lowered or "received" in lowered or "found" in lowered:
        type_key = "loot"
    elif "achievement" in lowered or "completed" in lowered:
        type_key = "achievement"
    elif "unlocked" in lowered:
        type_key = "unlock"

    skill = detect_activity_skill(combined) if type_key == "level" else None
    fallback = ACTIVITY_TYPE_META["activity"]
    meta = ACTIVITY_TYPE_META.get(type_key, fallback)
    color = SKILL_COLORS.get(skill, meta["color"]) if skill else meta["color"]
    return {
        "type_key": type_key,
        "type_label": meta["label"],
        "skill": skill,
        "color": color,
    }


# ---------------------------------------------------------------------------
# Main dashboard query
# ---------------------------------------------------------------------------


def get_dashboard_data() -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT s.*, p.username
            FROM snapshots s
            LEFT JOIN players p ON p.id = s.player_id
            ORDER BY s.timestamp DESC
            LIMIT 1
            """
        )
        latest = cur.fetchone()
        if not latest:
            return None

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        cutoff_today = today_start.strftime("%Y-%m-%d %H:%M:%S")
        prev_today = get_window_baseline(cur, cutoff_today, latest)

        cutoff_24h = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        prev_24h = get_window_baseline(cur, cutoff_24h, latest)

        cutoff_7d = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        prev_7d = get_window_baseline(cur, cutoff_7d, latest)

        # ------------------------------------------------------------------
        # Skills
        # ------------------------------------------------------------------
        cur.execute(
            "SELECT skill, level, xp, rank FROM skills WHERE snapshot_id = ?",
            (latest["id"],),
        )
        current_skills = cur.fetchall()

        prev_skills_map: dict[str, int] = {}
        prev_levels_map: dict[str, int] = {}
        if prev_today:
            cur.execute(
                "SELECT skill, xp, level FROM skills WHERE snapshot_id = ?",
                (prev_today["id"],),
            )
            for r in cur.fetchall():
                prev_skills_map[r["skill"]] = r["xp"]
                prev_levels_map[r["skill"]] = r["level"]

        skills_data: list[dict] = []
        level_candidates: list[dict] = []
        levels_gained_today = 0

        for s in current_skills:
            gain = s["xp"] - prev_skills_map.get(s["skill"], s["xp"])
            prev_level = prev_levels_map.get(s["skill"], s["level"])
            levels_gained_today += max(0, s["level"] - prev_level)
            remaining_xp = xp_to_next_level(s["skill"], s["level"], s["xp"])
            if remaining_xp > 0:
                level_candidates.append(
                    {
                        "skill": s["skill"],
                        "current_level": s["level"],
                        "target_level": s["level"] + 1,
                        "xp_to_next": remaining_xp,
                        "xp_to_next_display": format_skill_xp(remaining_xp),
                    }
                )
            skills_data.append(
                {
                    "skill": s["skill"],
                    "level": s["level"],
                    "xp": s["xp"],
                    "xp_gain": gain,
                    "xp_display": format_skill_xp(s["xp"]),
                    "xp_gain_display": format_skill_xp(gain),
                    "progress": calculate_progress(s["skill"], s["level"], s["xp"]),
                    "color": SKILL_COLORS.get(s["skill"], "#a0a0a0"),
                }
            )

        order_map = {name: i for i, name in enumerate(RS3_ORDER)}
        skills_data.sort(key=lambda x: order_map.get(x["skill"], 999))
        active_skills = sorted(
            [s for s in skills_data if s["xp_gain"] > 0],
            key=lambda s: s["xp_gain"],
            reverse=True,
        )
        closest_levels = sorted(level_candidates, key=lambda s: s["xp_to_next"])[:3]

        # ------------------------------------------------------------------
        # Activities
        # ------------------------------------------------------------------
        cur.execute("SELECT id, text, date, details FROM activities")
        activities: list[dict] = []
        for row in cur.fetchall():
            parsed = parse_activity_ts(row["date"])
            meta = classify_activity_meta(row["text"], row["details"])
            activities.append(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "date": row["date"],
                    "details": row["details"],
                    "date_iso": parsed.isoformat().replace("+00:00", "Z")
                    if parsed
                    else None,
                    "sort_ts": parsed or datetime.min.replace(tzinfo=timezone.utc),
                    **meta,
                }
            )
        activities.sort(key=lambda a: (a["sort_ts"], a["id"]), reverse=True)

        today_quests_finished = sum(
            1
            for a in activities
            if a["type_key"] == "quest" and a["sort_ts"] >= today_start
        )

        # Strip internal sort_ts before handing to template
        activities_out = [
            {k: v for k, v in a.items() if k != "sort_ts"} for a in activities
        ]

        # ------------------------------------------------------------------
        # 30-day XP history (sidebar chart)
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT timestamp, total_xp
            FROM snapshots
            WHERE timestamp >= datetime('now', '-30 days')
            ORDER BY timestamp ASC
            """
        )
        history = cur.fetchall()

        # ------------------------------------------------------------------
        # Derived stats
        # ------------------------------------------------------------------
        latest_dict = dict(latest)
        latest_dict["total_xp_display"] = format_total_xp(latest["total_xp"])

        xp_today = max(0, latest["total_xp"] - prev_today["total_xp"])
        rank_delta = prev_today["overall_rank"] - latest["overall_rank"]
        if rank_delta > 0:
            rank_delta_display = f"+{rank_delta:,}"
            rank_delta_class = "xp-gain-positive"
        elif rank_delta < 0:
            rank_delta_display = f"-{abs(rank_delta):,}"
            rank_delta_class = "xp-gain-negative"
        else:
            rank_delta_display = "0"
            rank_delta_class = ""

        xp_24h = latest["total_xp"] - prev_24h["total_xp"]
        xp_7d = latest["total_xp"] - prev_7d["total_xp"]

        return {
            "latest": latest_dict,
            "today_highlights": {
                "xp_today": xp_today,
                "xp_today_display": format_total_xp(xp_today),
                "levels_gained_today": levels_gained_today,
                "quests_finished_today": today_quests_finished,
                "rank_delta_today": rank_delta,
                "rank_delta_today_display": rank_delta_display,
                "rank_delta_today_class": rank_delta_class,
            },
            "xp_24h": xp_24h,
            "xp_7d": xp_7d,
            "xp_24h_display": format_total_xp(xp_24h),
            "xp_7d_display": format_total_xp(xp_7d),
            "player_name": latest["username"] or "Unknown Player",
            "top_gainers_today": [
                {"skill": s["skill"], "xp_gain_display": s["xp_gain_display"]}
                for s in active_skills[:5]
            ],
            "closest_levels": closest_levels,
            "skills": skills_data,
            "activities": activities_out,
            "timestamps": [r["timestamp"] + "Z" for r in history],
            "xp_history": [scale_total_xp(r["total_xp"]) for r in history],
        }
```

#### services/charts.py
```python
"""
Time-window and XP-aggregation helpers.

Pure functions only — no DB access, no FastAPI imports.  All chart and
history endpoints delegate their heavy lifting here.
"""

from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# XP scaling / formatting
# ---------------------------------------------------------------------------

XP_SCALE_SKILL = 10  # skill XP is stored ×10 in the DB


def scale_skill_xp(value: int | None) -> float:
    return (value or 0) / XP_SCALE_SKILL


def scale_total_xp(value: int | None) -> int:
    return value or 0


def format_skill_xp(value: int | None) -> str:
    scaled = scale_skill_xp(value)
    return f"{scaled:,.1f}".rstrip("0").rstrip(".")


def format_total_xp(value: int | None) -> str:
    return f"{int(scale_total_xp(value)):,}"


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------


def parse_snapshot_ts(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def parse_activity_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%d-%b-%Y %H:%M", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Period / timeframe normalisation
# ---------------------------------------------------------------------------


def normalize_bucket(timeframe: str) -> str:
    return {
        "hour": "hour",
        "day": "day",
        "week": "week",
        "month": "month",
        "all": "day",
    }.get(timeframe, "day")


def normalize_period(period: str) -> str:
    return {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
        "all": "all",
    }.get(period, "day")


# ---------------------------------------------------------------------------
# Bucket arithmetic
# ---------------------------------------------------------------------------


def advance_bucket(dt: datetime, bucket: str) -> datetime:
    if bucket == "hour":
        return dt + timedelta(hours=1)
    if bucket == "day":
        return dt + timedelta(days=1)
    if bucket == "week":
        return dt + timedelta(weeks=1)
    if bucket == "month":
        if dt.month == 12:
            return dt.replace(year=dt.year + 1, month=1, day=1)
        return dt.replace(month=dt.month + 1, day=1)
    if bucket == "year":
        return dt.replace(year=dt.year + 1, month=1, day=1)
    return dt + timedelta(days=1)


def bucket_start(dt: datetime, bucket: str) -> datetime:
    if bucket == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if bucket == "day":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == "week":
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return day_start - timedelta(days=day_start.weekday())
    if bucket == "month":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if bucket == "year":
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def build_bucket_starts(start: datetime, end: datetime, bucket: str) -> list[datetime]:
    starts: list[datetime] = []
    current = start
    while current <= end:
        starts.append(current)
        current = advance_bucket(current, bucket)
    return starts


def format_bucket_label(dt: datetime, bucket: str) -> str:
    if bucket == "hour":
        return dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Window helpers
# ---------------------------------------------------------------------------


def get_period_window(
    period: str, now: datetime, earliest_ts: str | None = None
) -> tuple[datetime, datetime, str]:
    p = normalize_period(period)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if p == "day":
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=23)
        return start, end, "hour"

    if p == "week":
        end = today
        start = end - timedelta(days=6)
        return start, end, "day"

    if p == "month":
        end = today
        start = today.replace(day=1)
        return start, end, "day"

    if p == "year":
        end = today
        start = end - timedelta(days=364)
        return start, end, "day"

    # "all" — full history, daily buckets
    end = today
    if earliest_ts:
        earliest = parse_snapshot_ts(earliest_ts)
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end
    return start, end, "day"


def get_timeframe_window(
    timeframe: str, now: datetime, earliest_ts: str | None = None
) -> tuple[datetime, datetime, str]:
    t = timeframe if timeframe in {"hour", "day", "week", "month", "all"} else "day"

    if t == "hour":
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=23)
        return start, end, "hour"

    if t == "day":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=6)
        return start, end, "day"

    if t == "week":
        end = bucket_start(now, "week")
        start = end - timedelta(weeks=7)
        return start, end, "week"

    if t == "month":
        end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = end.replace(month=1)
        return start, end, "month"

    # "all" — full history, daily buckets
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if earliest_ts:
        earliest = parse_snapshot_ts(earliest_ts)
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end
    return start, end, "day"


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def aggregate_bucket_gains(
    rows, bucket: str, starts: list[datetime], value_key: str, scale_fn=scale_total_xp
) -> list[float | int]:
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values: list[float | int] = []
    idx = 0
    previous_close = None
    first_start = starts[0]

    while idx < len(parsed) and parsed[idx][0] < first_start:
        previous_close = parsed[idx][1]
        idx += 1

    for b_start in starts:
        b_end = advance_bucket(b_start, bucket)
        bucket_close = previous_close
        while idx < len(parsed) and parsed[idx][0] < b_end:
            bucket_close = parsed[idx][1]
            idx += 1

        gain_raw = (
            0
            if (bucket_close is None or previous_close is None)
            else max(0, bucket_close - previous_close)
        )
        values.append(scale_fn(gain_raw))
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def aggregate_bucket_totals(
    rows, bucket: str, starts: list[datetime], value_key: str, scale_fn=scale_total_xp
) -> list[float | int]:
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values: list[float | int] = []
    idx = 0
    previous_close = None
    first_start = starts[0]

    while idx < len(parsed) and parsed[idx][0] < first_start:
        previous_close = parsed[idx][1]
        idx += 1

    for b_start in starts:
        b_end = advance_bucket(b_start, bucket)
        bucket_close = previous_close
        while idx < len(parsed) and parsed[idx][0] < b_end:
            bucket_close = parsed[idx][1]
            idx += 1

        values.append(scale_fn(bucket_close or 0))
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def aggregate_last_snapshot_totals(
    rows, bucket: str, starts: list[datetime], value_key: str, scale_fn=scale_total_xp
) -> list[float | int | None]:
    parsed = [
        (parse_snapshot_ts(row["timestamp"]), row[value_key])
        for row in rows
        if row["timestamp"] is not None
    ]
    parsed.sort(key=lambda t: t[0])

    if not starts:
        return []

    values: list[float | int | None] = []
    idx = 0
    previous_close = None
    first_start = starts[0]
    seen_data = False

    while idx < len(parsed) and parsed[idx][0] < first_start:
        previous_close = parsed[idx][1]
        idx += 1

    for b_start in starts:
        b_end = advance_bucket(b_start, bucket)
        bucket_close = previous_close
        while idx < len(parsed) and parsed[idx][0] < b_end:
            bucket_close = parsed[idx][1]
            idx += 1

        if bucket_close is None and not seen_data:
            values.append(None)
            continue

        seen_data = True
        values.append(
            scale_fn(bucket_close if bucket_close is not None else previous_close)
        )
        if bucket_close is not None:
            previous_close = bucket_close

    return values


def build_bucket_gains(rows, bucket: str, value_key: str) -> list[dict]:
    bucket_closing_xp: dict[datetime, int] = {}
    for row in rows:
        ts = parse_snapshot_ts(row["timestamp"])
        b = bucket_start(ts, bucket)
        bucket_closing_xp[b] = row[value_key]

    ordered = sorted(bucket_closing_xp.items(), key=lambda t: t[0])
    points: list[dict] = []
    prev_xp = None
    for b, closing_xp in ordered:
        gain_raw = 0 if prev_xp is None else max(0, closing_xp - prev_xp)
        points.append(
            {
                "timestamp": b.strftime("%Y-%m-%d %H:%M:%S") + "Z",
                "gain": scale_total_xp(gain_raw),
            }
        )
        prev_xp = closing_xp
    return points


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def get_window_baseline(cur, cutoff: str, latest):
    cur.execute(
        "SELECT * FROM snapshots WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
        (cutoff,),
    )
    baseline = cur.fetchone()
    if baseline:
        return baseline
    cur.execute(
        "SELECT * FROM snapshots WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT 1",
        (cutoff,),
    )
    return cur.fetchone() or latest


def series_has_data(values: list) -> bool:
    return any(value is not None for value in values)
```

#### pyproject.toml
```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "rs3-tracker"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.134.0",
    "httpx>=0.28.1",
    "jinja2>=3.1.6",
    "python-multipart>=0.0.20",
    "requests>=2.32.5",
    "uvicorn>=0.41.0",
]

[tool.setuptools]
py-modules = [
    "app",
    "collector",
    "config",
    "db",
    "log",
    "skills",
    "utils",
    "web",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["services*", "routes*"]

[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "ruff>=0.15.4",
]
```

#### routes/public.py
```python
"""
Public routes: dashboard page and all read-only API endpoints.

No auth, no admin logic.  Heavy lifting is delegated to the services layer.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from collector import collect_snapshot
from db import get_conn
from services.charts import (
    advance_bucket,
    aggregate_bucket_totals,
    aggregate_last_snapshot_totals,
    build_bucket_gains,
    build_bucket_starts,
    format_bucket_label,
    get_period_window,
    get_timeframe_window,
    normalize_bucket,
    normalize_period,
    scale_skill_xp,
    scale_total_xp,
    series_has_data,
)
from services.dashboard import get_dashboard_data
from web import templates

router = APIRouter()


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "data": get_dashboard_data()}
    )


# ---------------------------------------------------------------------------
# Chart / history API
# ---------------------------------------------------------------------------


@router.get("/api/skill_history/{skill_name}/{timeframe}")
def api_skill_history(skill_name: str, timeframe: str = "all"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(timestamp) as min_ts FROM snapshots")
        min_ts_row = cur.fetchone()
        min_ts = min_ts_row["min_ts"] if min_ts_row else None
        now = datetime.now(timezone.utc)
        start, end, bucket = get_timeframe_window(timeframe, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)

        cur.execute(
            """
            SELECT s.timestamp, sk.xp FROM skills sk
            JOIN snapshots s ON sk.snapshot_id = s.id
            WHERE sk.skill = ? AND s.timestamp < ?
            ORDER BY s.timestamp ASC
            """,
            (skill_name, advance_bucket(end, bucket).strftime("%Y-%m-%d %H:%M:%S")),
        )
        rows = cur.fetchall()
        totals = aggregate_bucket_totals(rows, bucket, starts, "xp", scale_skill_xp)
        labels = [format_bucket_label(b, bucket) for b in starts]
        return [{"timestamp": ts, "total": v} for ts, v in zip(labels, totals)]


@router.get("/api/skills_totals/{timeframe}")
def api_skills_totals(timeframe: str = "day"):
    from skills import RS3_ORDER

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(timestamp) as min_ts FROM snapshots")
        min_ts_row = cur.fetchone()
        min_ts = min_ts_row["min_ts"] if min_ts_row else None
        now = datetime.now(timezone.utc)
        start, end, bucket = get_timeframe_window(timeframe, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)
        end_exclusive = advance_bucket(end, bucket).strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            """
            SELECT s.timestamp, sk.skill, sk.xp
            FROM skills sk
            JOIN snapshots s ON sk.snapshot_id = s.id
            WHERE s.timestamp < ?
            ORDER BY s.timestamp ASC
            """,
            (end_exclusive,),
        )
        rows = cur.fetchall()

    per_skill_rows: dict[str, list] = {}
    for row in rows:
        per_skill_rows.setdefault(row["skill"], []).append(row)

    labels = [format_bucket_label(b, bucket) for b in starts]
    order_map = {name: i for i, name in enumerate(RS3_ORDER)}
    series = []
    for skill in sorted(per_skill_rows, key=lambda x: order_map.get(x, 999)):
        values = aggregate_bucket_totals(
            per_skill_rows[skill], bucket, starts, "xp", scale_skill_xp
        )
        series.append({"skill": skill, "totals": values})

    return {"labels": labels, "series": series}


@router.get("/api/chart/{skill_name}/{period}")
def api_chart(skill_name: str, period: str = "day"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MIN(timestamp) as min_ts FROM snapshots")
        min_ts_row = cur.fetchone()
        min_ts = min_ts_row["min_ts"] if min_ts_row else None

        now = datetime.now(timezone.utc)
        start, end, bucket = get_period_window(period, now, min_ts)
        starts = build_bucket_starts(start, end, bucket)
        end_exclusive = advance_bucket(end, bucket).strftime("%Y-%m-%d %H:%M:%S")

        if skill_name.lower() == "total":
            cur.execute(
                "SELECT timestamp, total_xp as xp FROM snapshots WHERE timestamp < ? ORDER BY timestamp ASC",
                (end_exclusive,),
            )
        else:
            cur.execute(
                """
                SELECT s.timestamp, sk.xp as xp
                FROM skills sk
                JOIN snapshots s ON sk.snapshot_id = s.id
                WHERE sk.skill = ? AND s.timestamp < ?
                ORDER BY s.timestamp ASC
                """,
                (skill_name, end_exclusive),
            )

        rows = cur.fetchall()

    scale_fn = scale_total_xp if skill_name.lower() == "total" else scale_skill_xp
    totals = aggregate_last_snapshot_totals(rows, bucket, starts, "xp", scale_fn)
    labels = [format_bucket_label(b, bucket) for b in starts]

    return {
        "labels": labels,
        "totals": totals,
        "has_gains": series_has_data(totals),
        "period": normalize_period(period),
        "skill": "Total" if skill_name.lower() == "total" else skill_name,
    }


@router.get("/api/total_xp_gains/{timeframe}")
def api_total_xp_gains(timeframe: str = "day"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT timestamp, total_xp FROM snapshots ORDER BY timestamp ASC")
        rows = cur.fetchall()
    return build_bucket_gains(rows, normalize_bucket(timeframe), "total_xp")


# ---------------------------------------------------------------------------
# Manual update trigger (intentionally unauthenticated — see REVIEW.md §B.security.1)
# ---------------------------------------------------------------------------


@router.post("/api/update")
async def manual_update():  # Added async
    try:
        await collect_snapshot()  # Added await
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

#### routes/admin.py
```python
"""
Admin routes — protected by HTTP Basic auth, CSRF tokens, and per-IP rate limiting.

Security model
--------------
* HTTP Basic credentials must match ADMIN_USERNAME / ADMIN_PASSWORD env vars.
* Every admin POST form must include a ``csrf_token`` hidden field whose value
  matches the ``csrf_token`` cookie set on the last admin GET.  This is the
  double-submit cookie pattern — no server-side session state required.
* Admin endpoints (GET and POST) are rate-limited to ADMIN_RATE_LIMIT requests
  per IP per minute.  The limit is intentionally generous enough to never
  affect legitimate use but blocks unsophisticated brute-force attempts.
"""

import secrets
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from collector import collect_snapshot
from config import ADMIN_PASSWORD, ADMIN_USERNAME, DB_PATH
from db import get_conn
from log import get_logger
from web import templates

logger = get_logger(__name__)

router = APIRouter()
_security = HTTPBasic()

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

_rate_lock = threading.Lock()
_ip_log: dict[str, list[datetime]] = defaultdict(list)

ADMIN_RATE_LIMIT = 60  # max requests per window per IP
ADMIN_RATE_WINDOW = timedelta(minutes=1)


def _client_ip(request: Request) -> str:
    """Return the real client IP, accounting for Cloud Run's X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    window_start = now - ADMIN_RATE_WINDOW
    with _rate_lock:
        _ip_log[ip] = [t for t in _ip_log[ip] if t > window_start]
        if len(_ip_log[ip]) >= ADMIN_RATE_LIMIT:
            logger.warning("Admin rate limit hit for IP %s", ip)
            raise HTTPException(
                status_code=429,
                detail="Too many requests — please wait a moment before trying again.",
            )
        _ip_log[ip].append(now)


# ---------------------------------------------------------------------------
# CSRF helpers  (double-submit cookie pattern)
# ---------------------------------------------------------------------------

_CSRF_COOKIE = "csrf_token"
_CSRF_FIELD = "csrf_token"
_CSRF_COOKIE_OPTS: dict = {
    "httponly": True,  # JS cannot read it; server injects value into forms
    "samesite": "strict",
    "secure": False,  # set True if the app is served exclusively over HTTPS
}


def _get_or_create_csrf_token(request: Request) -> str:
    """Return the CSRF token from the cookie, generating a fresh one if absent."""
    return request.cookies.get(_CSRF_COOKIE) or secrets.token_hex(32)


def _verify_csrf(request: Request, form_token: str) -> None:
    cookie_token = request.cookies.get(_CSRF_COOKIE, "")
    if not cookie_token or not secrets.compare_digest(cookie_token, form_token):
        logger.warning("CSRF check failed for IP %s", _client_ip(request))
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


# ---------------------------------------------------------------------------
# HTTP Basic auth dependency
# ---------------------------------------------------------------------------


def require_admin(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> HTTPBasicCredentials:
    _enforce_rate_limit(request)

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Admin credentials are not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD.",
        )

    user_ok = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


def _get_admin_overview() -> dict:
    table_counts = []
    with get_conn() as conn:
        cur = conn.cursor()
        for table in ("players", "snapshots", "skills", "activities"):
            cur.execute(f"SELECT COUNT(*) AS count FROM {table}")
            row = cur.fetchone()
            table_counts.append({"name": table, "count": row["count"]})

        cur.execute("SELECT timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 1")
        latest_row = cur.fetchone()

    db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "db_path": str(DB_PATH),
        "db_size_bytes": db_size_bytes,
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        "latest_snapshot_ts": latest_row["timestamp"] if latest_row else None,
        "table_counts": table_counts,
    }


def _render_admin(
    request: Request,
    *,
    csrf_token: str,
    sql: str = "",
    sql_error: str | None = None,
    sql_columns: list | None = None,
    sql_rows: list | None = None,
    sql_rowcount: int | None = None,
    message: str | None = None,
) -> HTMLResponse:
    response = templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "overview": _get_admin_overview(),
            "csrf_token": csrf_token,
            "sql": sql,
            "sql_error": sql_error,
            "sql_columns": sql_columns or [],
            "sql_rows": sql_rows or [],
            "sql_rowcount": sql_rowcount,
            "message": message,
        },
    )
    # Refresh the CSRF cookie on every admin response so it doesn't expire mid-session.
    response.set_cookie(_CSRF_COOKIE, csrf_token, **_CSRF_COOKIE_OPTS)
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
):
    csrf_token = _get_or_create_csrf_token(request)
    return _render_admin(request, csrf_token=csrf_token)


@router.post("/admin/sql", response_class=HTMLResponse)
def admin_run_sql(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    sql: str = Form(...),
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)

    statement = sql.strip()
    if not statement:
        return _render_admin(
            request, csrf_token=fresh_token, sql=sql, sql_error="SQL query is required."
        )

    # Reject multi-statement input.
    without_trailing = statement[:-1].strip() if statement.endswith(";") else statement
    if ";" in without_trailing:
        return _render_admin(
            request,
            csrf_token=fresh_token,
            sql=sql,
            sql_error="Only one SQL statement is allowed per execution.",
        )

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(statement)
            keyword = (
                statement.split(maxsplit=1)[0].lower() if statement.split() else ""
            )
            if keyword in {"select", "pragma", "with"}:
                rows = cur.fetchmany(200)
                columns = [d[0] for d in (cur.description or [])]
                return _render_admin(
                    request,
                    csrf_token=fresh_token,
                    sql=sql,
                    sql_columns=columns,
                    sql_rows=[dict(row) for row in rows],
                    message=f"Query succeeded. Showing up to 200 rows ({len(rows)} returned).",
                )
            conn.commit()
            return _render_admin(
                request,
                csrf_token=fresh_token,
                sql=sql,
                sql_rowcount=cur.rowcount,
                message=f"Statement succeeded. Rows affected: {cur.rowcount}.",
            )
    except sqlite3.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql=sql, sql_error=str(exc)
        )


@router.post("/admin/maintenance/update", response_class=HTMLResponse)
async def admin_collect_now(  # Added async
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        await collect_snapshot()  # Added await
        return _render_admin(
            request, csrf_token=fresh_token, message="Snapshot collected successfully."
        )
    except Exception as exc:
        return _render_admin(
            request,
            csrf_token=fresh_token,
            sql_error=f"Snapshot collection failed: {exc}",
        )


@router.post("/admin/maintenance/vacuum", response_class=HTMLResponse)
def admin_vacuum(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        with get_conn() as conn:
            conn.execute("VACUUM")
        return _render_admin(
            request, csrf_token=fresh_token, message="VACUUM completed."
        )
    except sqlite3.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql_error=f"VACUUM failed: {exc}"
        )


@router.post("/admin/maintenance/checkpoint", response_class=HTMLResponse)
def admin_checkpoint(
    request: Request,
    _: Annotated[HTTPBasicCredentials, Depends(require_admin)],
    csrf_token: str = Form(..., alias=_CSRF_FIELD),
):
    _verify_csrf(request, csrf_token)
    fresh_token = _get_or_create_csrf_token(request)
    try:
        with get_conn() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
        return _render_admin(
            request, csrf_token=fresh_token, message="WAL checkpoint completed."
        )
    except sqlite3.Error as exc:
        return _render_admin(
            request, csrf_token=fresh_token, sql_error=f"WAL checkpoint failed: {exc}"
        )
```

#### .github/workflows/ci.yml
```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  checks:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff pytest
          pip install .

      - name: Lint
        run: ruff check .

      - name: Run tests
        run: pytest

      - name: Validate Docker build
        run: docker build --tag rs3-tracker-ci .
```