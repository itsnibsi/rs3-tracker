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

Final note: this plan includes a targeted quest-field schema change, but it should run only in a dedicated migration phase and be explicitly reviewed with you before execution in hosted environments.
