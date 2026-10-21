import asyncio

from backend import server


class _IndexCollection:
    def __init__(self):
        self.indexes = []

    async def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))


class _IndexDatabase:
    def __init__(self):
        self.collections = {}

    def __getattr__(self, name):
        return self.collections.setdefault(name, _IndexCollection())


class _FailingIndexCollection(_IndexCollection):
    async def create_index(self, *args, **kwargs):
        raise RuntimeError("duplicate event IDs")


class _FailingIndexDatabase(_IndexDatabase):
    def __getattr__(self, name):
        if name == "resend_webhook_events":
            return self.collections.setdefault(name, _FailingIndexCollection())
        return super().__getattr__(name)


def test_resend_webhook_event_ids_have_unique_database_index(monkeypatch):
    database = _IndexDatabase()
    monkeypatch.setattr(server, "db", database)
    original_ready = server._RESEND_WEBHOOK_EVENT_INDEX_READY

    asyncio.run(server._ensure_indexes())

    assert (("id",), {"unique": True, "sparse": True}) in database.resend_webhook_events.indexes
    assert server._RESEND_WEBHOOK_EVENT_INDEX_READY is True

    monkeypatch.setattr(server, "db", _FailingIndexDatabase())
    asyncio.run(server._ensure_resend_webhook_event_index())
    assert server._RESEND_WEBHOOK_EVENT_INDEX_READY is False
    server._RESEND_WEBHOOK_EVENT_INDEX_READY = original_ready
