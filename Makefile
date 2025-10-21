all:
	uv venv
	uv pip install -r requirements.txt
	source .venv/bin/activate
	python3 -m src.main

run:
	python3 -m src.main
