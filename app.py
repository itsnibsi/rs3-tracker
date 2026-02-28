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
