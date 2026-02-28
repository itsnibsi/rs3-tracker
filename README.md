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

Example with `gcloud`:

```bash
gcloud run services update rs3-tracker \
  --region=europe-north1 \
  --set-env-vars=ADMIN_USERNAME=admin,ADMIN_PASSWORD='change-me'
```

For production, keep the password in Secret Manager and wire it into the service as an env var.
