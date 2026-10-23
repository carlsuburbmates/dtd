"""DF-052: real local Mongo proves the ceiling across independent workers.

The fixture owns an isolated ephemeral mongod and never connects to a provider.
"""
import asyncio
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import pytest

from services import ops_analyst


@pytest.fixture(scope="module")
def mongo_uri(tmp_path_factory):
    binary = shutil.which("mongod")
    if binary is None:
        pytest.skip("Local mongod required for datastore concurrency evidence")
    folder = tmp_path_factory.mktemp("df052-mongo")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    uri = f"mongodb://127.0.0.1:{port}/?directConnection=true"
    process = subprocess.Popen([
        binary, "--dbpath", str(folder), "--bind_ip", "127.0.0.1",
        "--port", str(port), "--logpath", str(folder / "mongo.log"),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = MongoClient(uri, serverSelectionTimeoutMS=100)
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail("Ephemeral mongod exited during startup")
            try:
                client.admin.command("ping")
                break
            except Exception:
                time.sleep(0.05)
        else:
            pytest.fail("Ephemeral mongod did not start within 10 seconds")
        yield uri
    finally:
        client.close()
        process.terminate()
        process.wait(timeout=10)


def case(identifier):
    return {"case_id": identifier, "severity": "high", "operational_state": "detected"}


def provider(generate):
    return SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))


def response():
    return SimpleNamespace(text=json.dumps({"summary": "Mock analysis"}), usage_metadata=None)


def test_budget_is_atomic_across_independent_modules_and_mongo_clients(mongo_uri, monkeypatch):
    async def run():
        clients = [AsyncIOMotorClient(mongo_uri), AsyncIOMotorClient(mongo_uri)]
        dbs = [client.df052_concurrency for client in clients]
        try:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await dbs[0].ops_ai_investigations.insert_many([
                {"created_at": f"{day}T00:01:00Z", "model_used": "gemini", "status": "completed"},
                # Legacy fallback might have incurred spend; seed it conservatively.
                {"created_at": f"{day}T00:02:00Z", "model_used": "deterministic_analyst_fallback", "status": "completed"},
                {"created_at": "2000-01-01T00:00:00Z", "model_used": "gemini", "status": "completed"},
            ])
            workers = []
            for index in range(2):
                spec = importlib.util.spec_from_file_location(f"df052_worker_{index}", Path(ops_analyst.__file__))
                worker = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(worker)
                monkeypatch.setattr(worker, "OPS_AI_DAILY_BUDGET", 5)
                workers.append(worker)
            calls = 0

            async def generate(**kwargs):
                nonlocal calls
                calls += 1
                await asyncio.sleep(0.01)
                return response()

            results = await asyncio.gather(*[
                workers[i % 2].analyze_incident(
                    dbs[i % 2], case(f"parallel_{i}"), override_client=provider(generate)
                ) for i in range(40)
            ])
            assert calls == 3
            assert sum(r["status"] == "completed" for r in results) == 3
            assert sum(r["status"] == "budget_exhausted" for r in results) == 37
            ledger = await dbs[0].ops_ai_investigations.find_one({"_id": f"ops_ai_daily_budget:{day}"})
            assert ledger["used"] == 5
            assert await workers[1].check_daily_budget(dbs[1]) == (False, 5, 5)
        finally:
            await clients[0].drop_database("df052_concurrency")
            for client in clients:
                client.close()
    asyncio.run(run())


@pytest.mark.parametrize("failure", ["timeout", "malformed", "provider_error"])
def test_failed_inference_keeps_spent_slot(mongo_uri, monkeypatch, failure):
    async def run():
        client = AsyncIOMotorClient(mongo_uri)
        db = client.df052_failure
        monkeypatch.setattr(ops_analyst, "OPS_AI_DAILY_BUDGET", 1)
        monkeypatch.setattr(ops_analyst.ai_service, "record_degradation_event", AsyncMock())
        if failure == "malformed":
            generate = AsyncMock(return_value=SimpleNamespace(text="invalid JSON", usage_metadata=None))
        else:
            error = asyncio.TimeoutError("mock timeout") if failure == "timeout" else RuntimeError("mock failure")
            generate = AsyncMock(side_effect=error)
        try:
            first = await ops_analyst.analyze_incident(db, case("failed"), override_client=provider(generate))
            assert first["model_used"] == "deterministic_analyst_fallback"
            cached = await ops_analyst.analyze_incident(db, case("failed"), override_client=provider(generate))
            assert cached["cached"] is True
            blocked = await ops_analyst.analyze_incident(db, case("different"), override_client=provider(generate))
            assert blocked["status"] == "budget_exhausted"
            assert generate.await_count == 1
            assert await ops_analyst.check_daily_budget(db) == (False, 1, 1)
        finally:
            await client.drop_database("df052_failure")
            client.close()
    asyncio.run(run())


def test_no_client_does_not_consume_or_initialize_budget(mongo_uri, monkeypatch):
    async def run():
        client = AsyncIOMotorClient(mongo_uri)
        db = client.df052_no_client
        monkeypatch.setattr(ops_analyst.ai_service, "get_gemini_client", lambda: None)
        try:
            result = await ops_analyst.analyze_incident(db, case("offline"))
            assert result["model_used"] == "deterministic_analyst_fallback"
            assert result["status"] == "completed"
            assert await db.ops_ai_investigations.count_documents({"document_type": "daily_attempt_budget"}) == 0
            assert (await ops_analyst.check_daily_budget(db))[1] == 0
        finally:
            await client.drop_database("df052_no_client")
            client.close()
    asyncio.run(run())
