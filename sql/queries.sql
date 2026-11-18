-- Exact application GQL. Bind the STRING parameter @order_id to A-1043.
-- Run one block at a time. Source records are the original fictional fixture.
-- order
GRAPH `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundGraph`
MATCH (o:`Order`)
WHERE o.order_id = @order_id
RETURN o.order_id AS order_id, o.item AS item,
       o.amount_usd AS amount_usd, o.placed_days_ago AS placed_days_ago;

-- payment
GRAPH `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundGraph`
MATCH evidence = (o:`Order`)-[:HAS_PAYMENT]->(p:Payment)
WHERE o.order_id = @order_id
RETURN o.order_id AS order_id, p.payment_id AS payment_id,
       p.method AS method, p.settled AS settled,
       p.chargeback_open AS chargeback_open, TO_JSON(evidence) AS evidence_path;

-- history
GRAPH `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundGraph`
MATCH evidence = (o:`Order`)<-[:PLACED]-(c:Customer)-[:HAS_HISTORY]->(h:RefundHistory)
WHERE o.order_id = @order_id
RETURN o.order_id AS order_id, c.customer_id AS customer_id,
       c.account_age_days AS account_age_days,
       h.prior_refunds_12mo AS prior_refunds_12mo,
       TO_JSON(evidence) AS evidence_path;

-- context
GRAPH `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundGraph`
MATCH payment_path = (c:Customer)-[:PLACED]->(o:`Order`)-[:HAS_PAYMENT]->(p:Payment),
      history_path = (c)-[:HAS_HISTORY]->(h:RefundHistory)
WHERE o.order_id = @order_id
RETURN c.customer_id AS customer_id, c.account_age_days AS account_age_days,
       o.order_id AS order_id, o.item AS item, o.amount_usd AS amount_usd,
       o.placed_days_ago AS placed_days_ago, p.method AS method,
       p.settled AS settled, p.chargeback_open AS chargeback_open,
       h.prior_refunds_12mo AS prior_refunds_12mo,
       TO_JSON(payment_path) AS payment_path, TO_JSON(history_path) AS history_path;
