"""Explicit local-demo configuration; no .env files or global auth changes."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = os.getenv('REFUND_BQ_PROJECT', 'neon-emitter-458622-e3')
DATASET = os.getenv('REFUND_BQ_DATASET', 'refund_graph_demo_20261016')
LOCATION = os.getenv('REFUND_BQ_LOCATION', 'US')
MODEL = 'gemini-3-flash-preview'
for value in (PROJECT, DATASET):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Invalid project or dataset identifier')
GRAPH = f'{PROJECT}.{DATASET}.RefundGraph'

