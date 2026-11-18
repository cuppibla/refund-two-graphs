-- Business values extracted from the original refund_static.py fixture.
CREATE SCHEMA IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016` OPTIONS(location="US", description="One refund, two graphs — original teaching fixture only");

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.Customers` AS SELECT "customer_for_A-1043" AS customer_id, 412 AS account_age_days;

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.Orders` AS SELECT "A-1043" AS order_id, 62.0 AS amount_usd, 12 AS placed_days_ago, "trail running shoes" AS item;

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.Payments` AS SELECT "payment_for_A-1043" AS payment_id, "visa" AS method, TRUE AS settled, FALSE AS chargeback_open;

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundHistory` AS SELECT "history_for_A-1043" AS history_id, 1 AS prior_refunds_12mo;

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.CustomerOrders` AS SELECT "customer_for_A-1043" AS customer_id, "A-1043" AS order_id;

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.OrderPayments` AS SELECT "A-1043" AS order_id, "payment_for_A-1043" AS payment_id;

CREATE TABLE IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.CustomerHistory` AS SELECT "customer_for_A-1043" AS customer_id, "history_for_A-1043" AS history_id;

CREATE PROPERTY GRAPH IF NOT EXISTS `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundGraph`
NODE TABLES (
  `neon-emitter-458622-e3.refund_graph_demo_20261016.Customers` AS Customers KEY (customer_id) LABEL Customer,
  `neon-emitter-458622-e3.refund_graph_demo_20261016.Orders` AS Orders KEY (order_id) LABEL `Order`,
  `neon-emitter-458622-e3.refund_graph_demo_20261016.Payments` AS Payments KEY (payment_id) LABEL Payment,
  `neon-emitter-458622-e3.refund_graph_demo_20261016.RefundHistory` AS RefundHistory KEY (history_id) LABEL RefundHistory
)
EDGE TABLES (
  `neon-emitter-458622-e3.refund_graph_demo_20261016.CustomerOrders` KEY (customer_id, order_id)
    SOURCE KEY (customer_id) REFERENCES Customers (customer_id)
    DESTINATION KEY (order_id) REFERENCES Orders (order_id) LABEL PLACED,
  `neon-emitter-458622-e3.refund_graph_demo_20261016.OrderPayments` KEY (order_id, payment_id)
    SOURCE KEY (order_id) REFERENCES Orders (order_id)
    DESTINATION KEY (payment_id) REFERENCES Payments (payment_id) LABEL HAS_PAYMENT,
  `neon-emitter-458622-e3.refund_graph_demo_20261016.CustomerHistory` KEY (customer_id, history_id)
    SOURCE KEY (customer_id) REFERENCES Customers (customer_id)
    DESTINATION KEY (history_id) REFERENCES RefundHistory (history_id) LABEL HAS_HISTORY
);
