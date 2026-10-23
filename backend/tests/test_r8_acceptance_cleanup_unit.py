"""R8 cleanup owns request IDs, never concurrent visitor diagnostics."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services import ai


def load_runner(filename):
    path = Path(__file__).resolve().parents[2] / 'scripts' / filename
    spec = importlib.util.spec_from_file_location(filename.replace('.', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matches(row, query):
    for key, value in query.items():
        if key == '$or':
            if not any(matches(row, branch) for branch in value):
                return False
            continue
        actual = row
        for part in key.split('.'):
            actual = actual.get(part) if isinstance(actual, dict) else None
        if isinstance(value, dict) and '$in' in value:
            if actual not in value['$in']:
                return False
        elif actual != value:
            return False
    return True


class Collection:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def delete_many(self, query):
        removed = [row for row in self.rows if matches(row, query)]
        self.rows = [row for row in self.rows if not matches(row, query)]
        return SimpleNamespace(deleted_count=len(removed))

    def count_documents(self, query):
        return sum(matches(row, query) for row in self.rows)

    def find(self, query, projection):
        return [row for row in self.rows if matches(row, query)]


class Database(dict):
    def __missing__(self, name):
        self[name] = Collection()
        return self[name]

    def __getattr__(self, name):
        return self[name]


@pytest.mark.parametrize('runner_name', ['run_sandbox_matching_acceptance.py', 'run_sandbox_matching_matrix.py'])
@pytest.mark.parametrize('known_id', [True, False])
def test_cleanup_preserves_other_matching_requests(runner_name, known_id):
    runner = load_runner(runner_name)
    db = Database()
    db['trainers'] = Collection([{'id': 'owned-trainer', 'test_run_id': 'owned-run'}])
    # Both requests selected the fixture, but only one belongs to this runner.
    db['match_events'] = Collection([
        {'id': item, 'result_ids': ['owned-trainer']} for item in ['owned', 'visitor']
    ])
    db['match_contexts'] = Collection([{'match_id': item} for item in ['owned', 'visitor']])
    db['ai_degradation_events'] = Collection([
        {'id': 'owned-diagnostic', 'operation': 'matching', 'match_id': 'owned'},
        {'id': 'visitor-diagnostic', 'operation': 'matching', 'match_id': 'visitor'},
        {'id': 'uncorrelated', 'operation': 'matching'},
        {'id': 'different-operation', 'operation': 'extraction', 'match_id': 'owned'},
    ])
    if 'matrix' in runner_name:
        runner._cleanup(db, trainer_ids=['owned-trainer'], match_ids=['owned'] if known_id else [], intro_ids=[])
    else:
        runner._cleanup(db, run_id='owned-run', trainer_id='owned-trainer', match_id='owned' if known_id else None)
    assert {row['id'] for row in db.match_events.rows} == ({'visitor'} if known_id else {'owned', 'visitor'})
    assert {row['match_id'] for row in db.match_contexts.rows} == ({'visitor'} if known_id else {'owned', 'visitor'})
    expected = {'visitor-diagnostic', 'uncorrelated', 'different-operation'}
    assert {row['id'] for row in db.ai_degradation_events.rows} == (expected if known_id else expected | {'owned-diagnostic'})
    assert db.trainers.rows == []


def test_degradation_context_is_concurrent_nested_and_exception_safe():
    async def run():
        stored = AsyncMock()
        db = SimpleNamespace(ai_degradation_events=SimpleNamespace(insert_one=stored))

        async def record(identifier):
            with ai.matching_degradation_context(identifier):
                await asyncio.sleep(0)
                event = await ai.record_degradation_event('timeout', 'mock', 'safe', 'matching', db=db)
                assert event['match_id'] == identifier
                other = await ai.record_degradation_event('timeout', 'mock', 'safe', 'extraction', db=db)
                assert 'match_id' not in other
        await asyncio.gather(record('request-a'), record('request-b'))
        with ai.matching_degradation_context('outer'):
            with pytest.raises(ValueError):
                with ai.matching_degradation_context('inner'):
                    raise ValueError('synthetic')
            outer = await ai.record_degradation_event('timeout', 'mock', 'safe', 'matching', db=db)
            assert outer['match_id'] == 'outer'
        outside = await ai.record_degradation_event('timeout', 'mock', 'safe', 'matching', db=db)
        assert 'match_id' not in outside
        assert stored.await_count == 6
    try:
        asyncio.run(run())
    finally:
        ai.clear_degradation_events()
