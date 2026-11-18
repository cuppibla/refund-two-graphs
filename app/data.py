"""Fixed GQL queries over the normalized original refund fixture."""
import json
from datetime import datetime, timezone
from decimal import Decimal

from google.cloud import bigquery

from .config import GRAPH, LOCATION, PROJECT
from .credentials import GcloudCredentials


def clean(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


QUERIES = {
    'order': f'''GRAPH `{GRAPH}`
MATCH (o:`Order`)
WHERE o.order_id = @order_id
RETURN o.order_id AS order_id, o.item AS item,
       o.amount_usd AS amount_usd, o.placed_days_ago AS placed_days_ago''',
    'payment': f'''GRAPH `{GRAPH}`
MATCH evidence = (o:`Order`)-[:HAS_PAYMENT]->(p:Payment)
WHERE o.order_id = @order_id
RETURN o.order_id AS order_id, p.payment_id AS payment_id,
       p.method AS method, p.settled AS settled,
       p.chargeback_open AS chargeback_open, TO_JSON(evidence) AS evidence_path''',
    'history': f'''GRAPH `{GRAPH}`
MATCH evidence = (o:`Order`)<-[:PLACED]-(c:Customer)-[:HAS_HISTORY]->(h:RefundHistory)
WHERE o.order_id = @order_id
RETURN o.order_id AS order_id, c.customer_id AS customer_id,
       c.account_age_days AS account_age_days,
       h.prior_refunds_12mo AS prior_refunds_12mo,
       TO_JSON(evidence) AS evidence_path''',
    'context': f'''GRAPH `{GRAPH}`
MATCH payment_path = (c:Customer)-[:PLACED]->(o:`Order`)-[:HAS_PAYMENT]->(p:Payment),
      history_path = (c)-[:HAS_HISTORY]->(h:RefundHistory)
WHERE o.order_id = @order_id
RETURN c.customer_id AS customer_id, c.account_age_days AS account_age_days,
       o.order_id AS order_id, o.item AS item, o.amount_usd AS amount_usd,
       o.placed_days_ago AS placed_days_ago, p.method AS method,
       p.settled AS settled, p.chargeback_open AS chargeback_open,
       h.prior_refunds_12mo AS prior_refunds_12mo,
       TO_JSON(payment_path) AS payment_path, TO_JSON(history_path) AS history_path''',
}


class EvidenceError(ValueError):
    pass


class GraphStore:
    def __init__(self):
        self.client = bigquery.Client(project=PROJECT, credentials=GcloudCredentials(), location=LOCATION)

    def fetch(self, kind, order_id):
        sql = QUERIES[kind]
        config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter('order_id', 'STRING', order_id)],
            use_query_cache=False,
            maximum_bytes_billed=100_000_000,
            labels={'app': 'refund-graph-demo', 'purpose': kind},
        )
        started = datetime.now(timezone.utc).isoformat()
        job = self.client.query(sql, job_config=config, location=LOCATION)
        rows = [clean(dict(r)) for r in job.result(timeout=90)]
        for row in rows:
            for key, val in list(row.items()):
                if key.endswith('path') and isinstance(val, str):
                    row[key] = json.loads(val)
        evidence = {
            'kind': kind, 'job_id': job.job_id, 'location': LOCATION,
            'project': PROJECT, 'started_at_utc': started,
            'sql': sql, 'parameters': {'order_id': order_id},
            'row_count': len(rows), 'rows': rows,
            'total_bytes_processed': job.total_bytes_processed,
            'cache_hit': job.cache_hit,
        }
        if len(rows) != 1:
            raise EvidenceError(f'{kind}: expected one record for {order_id}, found {len(rows)}. No decision made.')
        return evidence

