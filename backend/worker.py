from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import sentry_sdk

from services import ai as ai_service
from services import engine as autonomy
import server

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dtd.worker")

sentry_dsn = (os.environ.get("SENTRY_DSN") or "").strip()
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=(os.environ.get("SENTRY_ENVIRONMENT") or "development").strip(),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )

db = server.db
mongo_client = server.mongo_client


async def ensure_runtime_baseline() -> None:
    # Worker is the only process that should own autonomy loops in hosted mode.
    run_loops_in_api = (os.environ.get("RUN_AUTONOMY_IN_API") or "0").strip() == "1"
    if run_loops_in_api:
        raise RuntimeError("RUN_AUTONOMY_IN_API must be 0 when running worker process.")
    await server.on_startup()


async def main() -> None:
    await ensure_runtime_baseline()

    tasks = autonomy.schedule_all(db, ai_service)
    logger.info("worker scheduled %s autonomous loops", len(tasks))
    if not tasks:
        raise RuntimeError("No autonomous loops scheduled; check worker configuration.")
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
