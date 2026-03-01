# RS3 Tracker

A personal RuneScape 3 progress tracker. Collects hourly snapshots from the RuneMetrics API and displays XP history, skill progress, and activity feed on a dashboard.

## Architecture overview

```
app.py                  — FastAPI composition root (lifespan, mounts, router inclusion)
collector.py            — RuneMetrics API fetch + DB ingestion
config.py               — All env/config parsing with defaults
db.py                   — Connection pool, base schema, migration runner, indexes
skills.py               — Canonical skill metadata (names, order, colors, caps, activity taxonomy)
utils.py                — XP/level math (progress bars, xp-to-next-level)
web.py                  — Shared Jinja2Templates instance
routes/
  public.py             — Dashboard page + all read-only API endpoints
  admin.py              — Admin page + maintenance endpoints (auth, CSRF, rate limiting)
services/
  dashboard.py          — Dashboard data assembly and activity helpers
  charts.py             — Chart data, windowing/bucketing, XP formatting
  admin.py              — Admin DB overview query
static/js/
  feed.js               — Activity feed: fetch, group by day, render cards
  charts.js             — Total XP sidebar chart + skill history modal
templates/
  index.html            — Dashboard template
  admin.html            — Admin template
```

Ingestion is deliberately decoupled from the web process — see **Collector scheduling** below.

## Collector scheduling

Hourly snapshot collection is triggered by Cloud Scheduler rather than running inside the web process. This prevents duplicate collections when Cloud Run scales to multiple instances and decouples ingestion health from web server health.

The target endpoint is `POST /api/update`. Cloud Scheduler hits it on a cron schedule. The admin page retains a manual "Collect Snapshot Now" button as a fallback.

See `cloudscheduler.yaml` for full setup and management commands.

## Database

The app uses **PostgreSQL** via [Neon](https://neon.tech). The connection string is passed via `DATABASE_URL` environment variable.

Schema is created by `init_db()` on startup. Versioned migrations are tracked in the `schema_migrations` table and applied automatically at startup. To run migrations manually:

```bash
python db.py migrate
```

## Admin page

The app exposes a protected admin page at `/admin` with:

- A SQL console (single statement per run, max 200 result rows shown)
- Snapshot collection trigger
- `VACUUM` and WAL checkpoint maintenance actions
- DB overview (table row counts, latest snapshot timestamp)

Admin endpoints are protected by HTTP Basic auth, CSRF tokens (double-submit cookie pattern), and per-IP rate limiting.

### Configure admin credentials

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

2. Grant the Cloud Run service account access:

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

`cloudbuild.yaml` supports optional substitutions for admin secrets and the database URL:

- `_ADMIN_USERNAME_SECRET` — defaults to `rs3-admin-username`
- `_ADMIN_PASSWORD_SECRET` — defaults to `rs3-admin-password`
- `_DBURL` — defaults to `rs3-tracker-dburl`

Set these in your Cloud Build trigger to auto-bind secrets on every deploy. If left empty, deploy still succeeds but the env vars must already exist on the service.

## Automated checks

GitHub Actions workflow: `.github/workflows/ci.yml`

Validates every push and pull request with:

1. `ruff check .`
2. `pytest`
3. `docker build --tag rs3-tracker-ci .`

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (Neon) |
| `RS3_USERNAME` | No | `Varxis` | RuneScape username to track |
| `ADMIN_USERNAME` | No | — | Admin HTTP Basic username; omit to disable admin |
| `ADMIN_PASSWORD` | No | — | Admin HTTP Basic password |
| `SECRET_KEY` | No | random | CSRF token signing key; set for stability across restarts |
| `LOG_LEVEL` | No | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |