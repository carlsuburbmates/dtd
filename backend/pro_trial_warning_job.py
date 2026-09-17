from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlencode

import server
from services import pro_trials


def _billing_url(trainer: dict) -> str:
    trainer_id = str(trainer.get("id") or "")
    token = server._issue_trainer_action_token(trainer_id=trainer_id)
    base = (os.environ.get("FRONTEND_BASE_URL") or "https://dogtrainersdirectory.com.au").strip().rstrip("/")
    return f"{base}/trainer/billing?{urlencode({'trainerId': trainer_id, 'token': token})}"


async def main() -> None:
    try:
        summary = await pro_trials.process_expiry_warnings(server.db, billing_url_factory=_billing_url)
        print(json.dumps(summary, sort_keys=True))
        if summary.get("failed"):
            raise RuntimeError("one or more Pro trial warnings failed")
    finally:
        server.mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())
