"""Local-only teaching UI; real BigQuery queries and real ADK review/resume."""
import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import GRAPH, MODEL, ROOT
from .data import GraphStore
from .workflow import RefundRun, ReviewDecision

api = FastAPI(title='One refund, two graphs')
store = GraphStore()
runs = {}


class StartRequest(BaseModel):
    order_id: str = Field(default='A-1043', pattern=r'^[A-Za-z0-9_-]{1,64}$')


@api.get('/')
async def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@api.get('/api/config')
async def config():
    return {'graph': GRAPH, 'model': MODEL,
            'provenance': json.loads((ROOT / 'data' / 'source-fixture.json').read_text())}


@api.get('/api/graph')
async def graph(order_id: str = 'A-1043'):
    try:
        return await asyncio.to_thread(store.fetch, 'context', order_id)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc


@api.post('/api/runs', status_code=202)
async def start(body: StartRequest):
    if sum(r.status == 'running' for r in runs.values()) >= 3:
        raise HTTPException(429, 'Three runs are already active. Wait for one to finish.')
    run = RefundRun(order_id=body.order_id, store=store)
    runs[run.id] = run
    run.task = asyncio.create_task(run.start())
    return run.snapshot()


@api.get('/api/runs/{run_id}')
async def status(run_id: str):
    if run_id not in runs:
        raise HTTPException(404, 'Run not found. Local sessions are lost when the server restarts.')
    return runs[run_id].snapshot()


@api.post('/api/runs/{run_id}/review', status_code=202)
async def review(run_id: str, body: ReviewDecision):
    if run_id not in runs:
        raise HTTPException(404, 'Run not found')
    run = runs[run_id]
    if run.status != 'awaiting_review' or run.lock.locked():
        raise HTTPException(409, 'This run is not waiting for a review.')
    # Claim the review synchronously, before another request can submit it.
    run.status = 'review_submitted'

    async def finish_review():
        run.status = 'awaiting_review'
        await run.resume(body.approve, body.note)

    run.task = asyncio.create_task(finish_review())
    return run.snapshot()


api.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

