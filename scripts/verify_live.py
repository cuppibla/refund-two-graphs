"""One real BigQuery + ADK + Gemini run per reviewer outcome. Saves evidence."""
import asyncio
import json

from app.config import ROOT
from app.workflow import RefundRun


async def main():
    reports=[]
    for approve in (True, False):
        run=RefundRun()
        await run.start()
        if run.status != 'awaiting_review':
            raise AssertionError(run.snapshot())
        before = [e for e in run.trace if e['node'].startswith('fetch_')]
        assert len(run.evidence)==3 and not run.message
        await run.resume(approve, 'Approved as a goodwill exception for this demonstration.' if approve else 'The reviewer declined the discretionary exception for this demonstration.')
        report=run.snapshot()
        path=ROOT/'evidence'/('live-approve.json' if approve else 'live-decline.json')
        path.write_text(json.dumps(report,indent=2)+'\n')
        assert run.status == 'complete', run.error
        assert run.message.strip(), 'No generated draft captured'
        assert before == [e for e in run.trace if e['node'].startswith('fetch_')]
        assert run.case['amount_usd']==62 and run.case['policy_route']=='MANUAL_REVIEW'
        expected='approve_notice' if approve else 'denial_notice'
        assert run.nodes[expected]=='done'
        assert ('denial_notice' if approve else 'approve_notice') not in run.nodes
        reports.append({'approved':approve,'status':run.status,'query_job_ids':[e['job_id'] for e in run.evidence.values()], 'draft':run.message})
    print(json.dumps(reports,indent=2))


if __name__=='__main__':
    asyncio.run(main())
