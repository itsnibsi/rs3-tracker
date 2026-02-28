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
