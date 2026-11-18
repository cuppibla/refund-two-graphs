import pytest

from app.policy import refund_policy, validate_case


@pytest.mark.parametrize('amount,days,dispute,priors,expected', [
    (62, 12, False, 1, 'MANUAL_REVIEW'),
    (49.99, 30, False, 2, 'AUTO_APPROVE'),
    (50, 30, False, 2, 'MANUAL_REVIEW'),
    (49.99, 31, False, 2, 'DENY'),
    (20, 5, True, 0, 'DENY'),
    (20, 5, False, 3, 'MANUAL_REVIEW'),
])
def test_policy_boundaries(amount, days, dispute, priors, expected):
    assert refund_policy(amount, days, dispute, priors) == expected


@pytest.mark.parametrize('change', [
    {'amount_usd': None}, {'chargeback_open': 'false'},
    {'prior_refunds_12mo': -1}, {'placed_days_ago': 1.5},
    {'amount_usd': float('nan')}, {'order_id': ''},
])
def test_invalid_evidence_cannot_reach_policy(change):
    case = {'order_id': 'A-1043', 'amount_usd': 62, 'placed_days_ago': 12,
            'chargeback_open': False, 'prior_refunds_12mo': 1}
    with pytest.raises(ValueError):
        validate_case(case | change)

