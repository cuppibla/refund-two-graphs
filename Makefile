.PHONY: install setup playground test verify-live eval eval-all lint

install:
	uv sync --locked

setup:
	uv run python -m scripts.setup_bigquery

playground:
	uv run uvicorn app.server:api --host 127.0.0.1 --port 8765

test:
	uv run pytest tests/unit tests/integration -q

verify-live:
	uv run python -m scripts.verify_live

eval:
	uv sync --locked --extra eval
	uv run python -m scripts.evaluate

eval-all: eval

lint:
	uvx ruff check app scripts tests eval_entry --select E9,F63,F7,F82
	node --check static/app.js
