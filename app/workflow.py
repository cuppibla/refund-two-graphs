"""Actual ADK Workflow. BigQuery reads, rules, review, and model drafting."""
import asyncio
import time
import uuid
from datetime import datetime, timezone

from google.adk import Context, Event, Runner, Workflow
from google.adk.events import RequestInput
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START, JoinNode, node
from google.genai import types
from pydantic import BaseModel, Field

from .agent import make_notice
from .data import GraphStore
from .policy import decision_reason, refund_policy, validate_case

REVIEW_ID = 'refund:review'


class ReviewDecision(BaseModel):
    approve: bool
    note: str = Field(min_length=1, max_length=500)


class RefundRun:
    def __init__(self, order_id='A-1043', store=None, model_enabled=True):
        self.id = str(uuid.uuid4())
        self.order_id = order_id
        self.store = store or GraphStore()
        self.model_enabled = model_enabled
        self.status = 'created'
        self.trace = []
        self.evidence = {}
        self.nodes = {}
        self.case = None
        self.pending = None
        self.message = ''
        self.error = None
        self.started = time.perf_counter()
        self.started_at_utc = datetime.now(timezone.utc).isoformat()
        self.lock = asyncio.Lock()
        self.task = None
        self.workflow = build_workflow(self)
        self.runner = Runner(node=self.workflow, app_name='refund_demo',
                             session_service=InMemorySessionService(), auto_create_session=True)

    def emit(self, node_name, status, detail=''):
        self.nodes[node_name] = status
        self.trace.append({'seconds': round(time.perf_counter() - self.started, 3),
                           'node': node_name, 'status': status, 'detail': detail})

    def snapshot(self):
        return {'id': self.id, 'order_id': self.order_id, 'status': self.status,
                'started_at_utc': self.started_at_utc, 'nodes': self.nodes.copy(),
                'trace': list(self.trace), 'evidence': self.evidence.copy(),
                'case': self.case, 'message': self.message, 'error': self.error,
                'model_enabled': self.model_enabled}

    async def consume(self, message):
        async for event in self.runner.run_async(user_id='demo', session_id=self.id, new_message=message):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    call = part.function_call
                    if call and call.name == 'adk_request_input':
                        self.pending = call
                    if part.text and not getattr(part, 'thought', False) and event.author in {'approve_notice', 'denial_notice'}:
                        self.message = part.text
            output = getattr(event, 'output', None)
            if not self.model_enabled and isinstance(output, str):
                self.message = output

    async def start(self):
        self.status = 'running'
        try:
            await self.consume(types.Content(role='user', parts=[types.Part(text=self.order_id)]))
            self.status = 'awaiting_review' if self.pending else 'complete'
        except Exception as exc:
            self.status, self.error = 'error', str(exc)
            self.emit('error', 'error', self.error)

    async def resume(self, approve, note):
        async with self.lock:
            if self.status != 'awaiting_review' or not self.pending:
                raise ValueError('This run is not awaiting a reviewer decision.')
            answer = ReviewDecision(approve=approve, note=note)
            pending = self.pending
            self.pending = None
            self.status = 'running'
            try:
                await self.consume(types.Content(role='user', parts=[types.Part(
                    function_response=types.FunctionResponse(
                        id=pending.id, name=pending.name, response=answer.model_dump(),
                    ))]))
                self.status = 'complete'
            except Exception as exc:
                self.status, self.error = 'error', str(exc)
                self.emit('error', 'error', self.error)


def build_workflow(run):
    async def fetch(kind, order_id):
        name = 'fetch_' + kind
        run.emit(name, 'running', f'Querying BigQuery Graph for {order_id}')
        try:
            evidence = await asyncio.to_thread(run.store.fetch, kind, order_id)
        except Exception:
            run.emit(name, 'error', 'No complete evidence returned')
            raise
        run.evidence[kind] = evidence
        run.emit(name, 'done', evidence['job_id'])
        return evidence['rows'][0]

    async def fetch_order(node_input: str) -> dict:
        return await fetch('order', node_input)

    async def fetch_payment(node_input: str) -> dict:
        return await fetch('payment', node_input)

    async def fetch_history(node_input: str) -> dict:
        return await fetch('history', node_input)

    join_case = JoinNode(name='join_case')

    def route_refund(node_input: dict):
        run.emit('join_case', 'done', 'All three fetches completed')
        parts = [node_input[n] for n in ('fetch_order', 'fetch_payment', 'fetch_history')]
        if any(p.get('order_id') != run.order_id for p in parts):
            raise ValueError('Evidence belongs to a different order; no decision made.')
        # Keep case facts separate from path payloads. Full paths remain in evidence.
        case = {k: v for part in parts for k, v in part.items() if not k.endswith('path')}
        validate_case(case)
        route = refund_policy(case['amount_usd'], case['placed_days_ago'],
                              case['chargeback_open'], case['prior_refunds_12mo'])
        case.update(policy_route=route, decision_reason=decision_reason(case, route),
                    decision={'AUTO_APPROVE': 'APPROVED', 'DENY': 'DECLINED', 'MANUAL_REVIEW': 'PENDING_REVIEW'}[route])
        run.case = case
        run.emit('route_refund', 'done', route)
        return Event(output=case, route=route)

    @node(rerun_on_resume=True)
    async def human_review(ctx: Context, node_input: dict):
        answer = ctx.resume_inputs.get(REVIEW_ID)
        if answer is None:
            run.emit('human_review', 'waiting', 'Waiting for an actual reviewer choice in the browser')
            yield RequestInput(interrupt_id=REVIEW_ID,
                               message=f"Review ${node_input['amount_usd']:g} for {node_input['order_id']}.",
                               payload=node_input, response_schema=ReviewDecision)
            return
        answer = ReviewDecision.model_validate(answer)
        case = {**node_input, 'reviewer_note': answer.note,
                'decision': 'APPROVED' if answer.approve else 'DECLINED'}
        run.case = case
        run.emit('human_review', 'done', case['decision'])
        yield Event(output=case, route='AUTO_APPROVE' if answer.approve else 'DENY')

    def notice(name):
        if not run.model_enabled:
            def recorded_notice(node_input: dict):
                run.emit(name, 'done', 'MODEL DISABLED: control-flow test only')
                run.message = f"CONTROL-FLOW TEST ONLY: {node_input['decision']} {node_input['order_id']}"
                return run.message
            recorded_notice.__name__ = name
            return recorded_notice
        agent = make_notice(name)

        async def before(callback_context):
            run.emit(name, 'running', 'Gemini is drafting the response from the decided case')

        async def after(callback_context):
            run.emit(name, 'done', 'Draft generated; no message sent or payment executed')

        agent.before_agent_callback = before
        agent.after_agent_callback = after
        return agent

    approve_notice = notice('approve_notice')
    denial_notice = notice('denial_notice')
    return Workflow(name='refund_decision', edges=[
        (START, (fetch_order, fetch_payment, fetch_history), join_case, route_refund),
        (route_refund, {'AUTO_APPROVE': approve_notice, 'MANUAL_REVIEW': human_review, 'DENY': denial_notice}),
        (human_review, {'AUTO_APPROVE': approve_notice, 'DENY': denial_notice}),
    ])

