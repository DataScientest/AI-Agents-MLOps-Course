.PHONY: help demo demo-linear demo-conditional demo-loop demo-human clean

# Default target
help:
	@echo "LangGraph Agent Patterns - Available Commands:"
	@echo ""
	@echo "  make demo              - Run all agent patterns"
	@echo "  make demo-linear       - Run linear workflow pattern only"
	@echo "  make demo-conditional  - Run conditional branching pattern only"
	@echo "  make demo-loop         - Run loop pattern only"
	@echo "  make demo-human        - Run human-in-the-loop pattern only"
	@echo ""
	@echo "  make clean             - Remove Python cache files"
	@echo ""

# Run all patterns
demo:
	@echo "Running all LangGraph agent patterns..."
	python3 -m src.main

# Run individual patterns
demo-linear:
	@echo "Running linear workflow pattern..."
	python3 -m src.main --pattern linear

demo-conditional:
	@echo "Running conditional branching pattern..."
	python3 -m src.main --pattern conditional

demo-loop:
	@echo "Running loop pattern..."
	python3 -m src.main --pattern loop

demo-human:
	@echo "Running human-in-the-loop pattern..."
	python3 -m src.main --pattern human

# Cleanup
clean:
	@echo "Cleaning Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Done!"

#test:
#	@echo "Running tests..."
#	pytest -v tests

# Alias for backwards compatibility
all: demo