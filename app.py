"""
Application composition root.

This file's only jobs:
  1. Create the FastAPI app and configure its lifespan.
  2. Mount static files.
  3. Include routers from routes/.

All logic lives in services/, routes/, and supporting modules.

Collector scheduling
--------------------
The hourly snapshot collection is intentionally NOT run here.  Running it
inside the web process causes duplicate collections when Cloud Run scales to
multiple instances, and ties ingestion availability to web server health.

Use Cloud Scheduler to POST /api/update on a cron schedule instead.
See cloudscheduler.yaml for the setup.  The admin page retains a manual
"Collect Snapshot Now" trigger as a fallback.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db import init_db
from log import configure_logging, get_logger
from routes.admin import router as admin_router
from routes.public import router as public_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    yield


app = FastAPI(lifespan=lifespan, title="RS3 Tracker")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(public_router)
app.include_router(admin_router)
