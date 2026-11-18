"""Offline orchestration tests; live runs are saved separately in evidence/."""
import json
import time

import pytest

from app.config import ROOT
from app.workflow import RefundRun


class FixtureStore:
    def __init__(self, missing=False):
        self.calls = []
        self.missing = missing
        self.fixture = json.loads((ROOT/'data'/'source-fixture.json').read_text())['sections']

    def fetch(self, kind, order_id):
        self.calls.append(kind)
        time.sleep(.03)
        if self.missing and kind == 'history':
            raise ValueError('Missing history: no decision made')
        row = {'order_id': order_id, **self.fixture['fetch_'+kind]['values']}
        return {'job_id': 'OFFLINE-TEST-'+kind, 'kind': kind, 'rows': [row]}


@pytest.mark.asyncio
@pytest.mark.parametrize('approve', [True, False])
async def test_review_interrupt_and_resume_without_duplicate_fetch(approve):
    store = FixtureStore()
    run = RefundRun(store=store, model_enabled=False)
    await run.start()
    assert run.status == 'awaiting_review', run.error
    assert run.pending and not run.message
    assert run.case['policy_route'] == 'MANUAL_REVIEW'
    assert not any('notice' in e['node'] for e in run.trace)
    starts = [e['seconds'] for e in run.trace if e['status']=='running']
    finishes = [e['seconds'] for e in run.trace if e['node'].startswith('fetch_') and e['status']=='done']
    assert max(starts) < min(finishes)
    assert run.trace.index(next(e for e in run.trace if e['node']=='join_case')) > max(i for i,e in enumerate(run.trace) if e['node'].startswith('fetch_'))
    await run.resume(approve, 'Explicit test reviewer decision')
    assert run.status == 'complete', run.error
    assert sorted(store.calls) == ['history','order','payment']
    notices = [e['node'] for e in run.trace if 'notice' in e['node']]
    assert notices == ['approve_notice' if approve else 'denial_notice']
    assert run.case['reviewer_note'] == 'Explicit test reviewer decision'
    with pytest.raises(ValueError, match='not awaiting'):
        await run.resume(approve, 'Duplicate response')


@pytest.mark.asyncio
async def test_missing_history_stops_the_decision():
    run = RefundRun(store=FixtureStore(missing=True), model_enabled=False)
    await run.start()
    assert run.status == 'error'
    assert run.case is None and not run.message and not run.pending
    assert 'route_refund' not in run.nodes

