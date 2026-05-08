from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import sentry_sdk

from services import ai as ai_service
from services import engine as autonomy
from services import runtime_control
from services.runtime_control import LoopRuntimeConfig
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


async def ensure_runtime_baseline() -> LoopRuntimeConfig:
    runtime = runtime_control.resolve_loop_runtime("worker")
    if runtime.loop_owner != "worker":
        raise RuntimeError(
            "Worker process started while loop owner is "
            f"'{runtime.loop_owner}'. Set AUTONOMY_LOOP_OWNER=worker for worker-owned runtime."
        )
    await server.on_startup(process_role="worker", allow_loop_schedule=False)
    return runtime


async def main() -> None:
    runtime = await ensure_runtime_baseline()

    tasks = autonomy.schedule_all(
        db,
        ai_service,
        owner_id=runtime.owner_id,
        lease_enabled=runtime.lease_enabled,
        lease_ttl_s=runtime.lease_ttl_s,
        lease_renew_s=runtime.lease_renew_s,
    )
    scheduled = max(0, len(tasks) - (1 if runtime.lease_enabled else 0))
    logger.info(
        "worker runtime: owner=%s source=%s lease=%s owner_id=%s scheduled_loops=%s",
        runtime.loop_owner,
        runtime.source,
        runtime.lease_enabled,
        runtime.owner_id,
        scheduled,
    )
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
