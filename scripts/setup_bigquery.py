"""Create only the isolated prototype dataset, tables, and property graph."""
import json
from datetime import datetime, timezone

from google.cloud import bigquery

from app.config import DATASET, GRAPH, LOCATION, PROJECT, ROOT
from app.data import GraphStore


def literal(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if type(value) in (int, float):
        return str(value)
    raise TypeError(value)


def main():
    f = json.loads((ROOT / 'data' / 'source-fixture.json').read_text())
    order = f['sections']['fetch_order']['values']
    payment = f['sections']['fetch_payment']['values']
    history = f['sections']['fetch_history']['values']
    ids = f['technical_ids']
    rows = {
        'Customers': {'customer_id': ids['customer_id'], 'account_age_days': history['account_age_days']},
        'Orders': order,
        'Payments': {'payment_id': ids['payment_id'], **payment},
        'RefundHistory': {'history_id': ids['history_id'], 'prior_refunds_12mo': history['prior_refunds_12mo']},
        'CustomerOrders': {'customer_id': ids['customer_id'], 'order_id': order['order_id']},
        'OrderPayments': {'order_id': order['order_id'], 'payment_id': ids['payment_id']},
        'CustomerHistory': {'customer_id': ids['customer_id'], 'history_id': ids['history_id']},
    }
    prefix = f'{PROJECT}.{DATASET}'
    statements = [f'CREATE SCHEMA IF NOT EXISTS `{prefix}` OPTIONS(location="{LOCATION}", description="One refund, two graphs — original teaching fixture only")']
    for name, values in rows.items():
        projection = ', '.join(f'{literal(v)} AS {k}' for k, v in values.items())
        statements.append(f'CREATE TABLE IF NOT EXISTS `{prefix}.{name}` AS SELECT {projection}')
    statements.append(f'''CREATE PROPERTY GRAPH IF NOT EXISTS `{GRAPH}`
NODE TABLES (
  `{prefix}.Customers` AS Customers KEY (customer_id) LABEL Customer,
  `{prefix}.Orders` AS Orders KEY (order_id) LABEL `Order`,
  `{prefix}.Payments` AS Payments KEY (payment_id) LABEL Payment,
  `{prefix}.RefundHistory` AS RefundHistory KEY (history_id) LABEL RefundHistory
)
EDGE TABLES (
  `{prefix}.CustomerOrders` KEY (customer_id, order_id)
    SOURCE KEY (customer_id) REFERENCES Customers (customer_id)
    DESTINATION KEY (order_id) REFERENCES Orders (order_id) LABEL PLACED,
  `{prefix}.OrderPayments` KEY (order_id, payment_id)
    SOURCE KEY (order_id) REFERENCES Orders (order_id)
    DESTINATION KEY (payment_id) REFERENCES Payments (payment_id) LABEL HAS_PAYMENT,
  `{prefix}.CustomerHistory` KEY (customer_id, history_id)
    SOURCE KEY (customer_id) REFERENCES Customers (customer_id)
    DESTINATION KEY (history_id) REFERENCES RefundHistory (history_id) LABEL HAS_HISTORY
)''')
    sql = ';\n\n'.join(statements) + ';\n'
    (ROOT / 'sql').mkdir(exist_ok=True)
    (ROOT / 'sql' / 'setup.sql').write_text('-- Business values extracted from the original refund_static.py fixture.\n' + sql)
    store = GraphStore()
    job = store.client.query(sql, location=LOCATION, job_config=bigquery.QueryJobConfig(labels={'app': 'refund-graph-demo', 'purpose': 'setup'}))
    list(job.result(timeout=120))
    result = store.fetch('context', order['order_id'])
    actual = result['rows'][0]
    for key, value in {**order, **payment, **history}.items():
        if actual[key] != value:
            raise ValueError(f'Existing dataset differs from fixture: {key}')
    # Verify each table's cardinality, including orphaned rows not reached by the graph.
    for table in rows:
        count = next(iter(store.client.query(f'SELECT COUNT(*) AS n FROM `{prefix}.{table}`').result())).n
        if count != 1:
            raise ValueError(f'{table} contains {count} rows; expected one original fixture row')
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'setup_job_id': job.job_id, 'dataset': prefix, 'graph': GRAPH,
              'source_sha256': f['source_sha256'], 'query': result,
              'verification': 'All original business values match; all seven tables have one row.'}
    (ROOT / 'evidence').mkdir(exist_ok=True)
    (ROOT / 'evidence' / 'bigquery-setup.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'setup_job_id': job.job_id, 'context_job_id': result['job_id'], 'values': {k: v for k, v in actual.items() if not k.endswith('path')}}))


if __name__ == '__main__':
    main()

