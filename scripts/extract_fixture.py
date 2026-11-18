"""Extract source literals without running the original demo or loading secrets."""
import ast
import hashlib
import json
import os
from pathlib import Path

from app.config import ROOT

SOURCE = Path(os.environ.get('REFUND_SOURCE', 'refund_static.py'))


def main():
    text = SOURCE.read_text()
    tree = ast.parse(text)
    sections = {}
    for item in tree.body:
        if isinstance(item, ast.AsyncFunctionDef) and item.name in {'fetch_order', 'fetch_payment', 'fetch_history'}:
            returns = [n for n in ast.walk(item) if isinstance(n, ast.Return)]
            if len(returns) != 1:
                raise ValueError('Expected one literal return per fetch')
            sections[item.name] = {'values': ast.literal_eval(returns[0].value), 'source_line': returns[0].lineno}
    if len(sections) != 3:
        raise ValueError('Missing original source fields')
    fixture = {
        'source': SOURCE.name, 'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'classification': 'Original fictional demo fixture; not production customer data.',
        'sections': sections,
        'technical_ids': {
            'customer_id': 'customer_for_A-1043',
            'payment_id': 'payment_for_A-1043',
            'history_id': 'history_for_A-1043',
        },
        'normalization_note': 'Technical IDs and relationship rows are newly assigned for this prototype. Business values are copied exactly from the original case. The one prior refund is a summary, not a reconstructed transaction.',
    }
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data' / 'source-fixture.json').write_text(json.dumps(fixture, indent=2) + '\n')
    print('Extracted original order/payment/history literals; no source code executed.')


if __name__ == '__main__':
    main()

