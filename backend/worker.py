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


async def ensure_indexes() -> None:
    await db.trainers.create_index("id", unique=True, sparse=True)
    await db.intros.create_index([("trainer_id", 1), ("created_at", -1)])
    await db.intros.create_index("ip")
    await db.intros.create_index(
        [("trainer_id", 1), ("idempotency_key", 1)],
        unique=True,
        partialFilterExpression={"idempotency_key": {"$exists": True, "$type": "string", "$gt": ""}},
        name="uniq_intro_idempotency_per_trainer",
    )
    await db.conversions.create_index([("intro_id", 1), ("billing_status", 1)])
    await db.engagements.create_index([("intro_id", 1), ("created_at", -1)])
    await db.credit_state.create_index("trainer_id", unique=True, name="uniq_credit_state_trainer")
    await db.credit_ledger.create_index("id", unique=True, name="uniq_credit_ledger_id")
    await db.credit_ledger.create_index("source_intro_id", unique=True, name="uniq_credit_ledger_source_intro")
    await db.submissions.create_index("status")
    await db.audit_log.create_index("ts")
    await db.pricing_state.create_index("suburb", unique=True)
    await db.system_state.create_index("key", unique=True)
    await db.discovery_queue.create_index("status")
    await db.config_snapshots.create_index("applied_at")


async def main() -> None:
    await ensure_indexes()
    await server._seed_if_empty()  # pylint: disable=protected-access
    await server._seed_discovery_if_empty()  # pylint: disable=protected-access

    try:
        await autonomy.recompute_ranking(db)
        await autonomy.recompute_pricing(db)
        await autonomy.update_health(db)
    except Exception:  # noqa: BLE001
        logger.exception("initial loop pass failed in worker")

    tasks = autonomy.schedule_all(db, ai_service)
    logger.info("worker scheduled %s autonomous loops", len(tasks))
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
