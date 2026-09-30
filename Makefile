all:
	uv sync
	uv run python -m src.main

run:
	uv run python -m src.main

test:
	uv run pytest
