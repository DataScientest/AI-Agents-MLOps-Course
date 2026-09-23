all:
	uv sync
	uv run python -m src.main

run:
	python3 -m src.main

test:
	uv run pytest
