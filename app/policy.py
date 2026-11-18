"""The original policy, plus explicit evidence validation at its boundary."""
from math import isfinite


def refund_policy(amount, days_ago, chargeback_open, priors):
    if chargeback_open or days_ago > 30:
        return 'DENY'
    if amount < 50 and priors < 3:
        return 'AUTO_APPROVE'
    return 'MANUAL_REVIEW'


def validate_case(case):
    required = ['order_id', 'amount_usd', 'placed_days_ago', 'chargeback_open', 'prior_refunds_12mo']
    if any(key not in case or case[key] is None for key in required):
        raise ValueError('Required refund evidence is missing; no decision made.')
    if not isinstance(case['order_id'], str) or not case['order_id']:
        raise ValueError('Missing order identifier')
    if type(case['chargeback_open']) is not bool:
        raise ValueError('chargeback_open must be a boolean')
    for key in ['amount_usd', 'placed_days_ago', 'prior_refunds_12mo']:
        value = case[key]
        if type(value) not in (int, float) or not isfinite(value) or value < 0:
            raise ValueError(f'Invalid {key}')
    for key in ['placed_days_ago', 'prior_refunds_12mo']:
        if not float(case[key]).is_integer():
            raise ValueError(f'{key} must be an integer')
    return case


def decision_reason(case, decision):
    if case['chargeback_open']:
        return 'The payment has an open chargeback.'
    if case['placed_days_ago'] > 30:
        return 'The order is outside the 30-day refund window.'
    if decision == 'AUTO_APPROVE':
        return 'Within 30 days, no open chargeback, amount under $50, and fewer than 3 prior refunds.'
    return 'Automatic approval requires an amount under $50 and fewer than 3 prior refunds; this case needs review.'

