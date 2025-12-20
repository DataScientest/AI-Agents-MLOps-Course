#!/bin/bash
# Script to run all Chapter 6 tests

set -e

echo "Starting Chapter 6 Test Suite..."

# 1. Run Unit Tests
echo "--- Running Unit Tests ---"
pytest tests/unit/ -v

# 2. Run Integration Tests
echo "--- Running Integration Tests ---"
pytest tests/integration/ -v

# 3. Run E2E Tests
echo "--- Running End-to-End Tests ---"
pytest tests/e2e/ -v

# 4. Run SLA Validation
echo "--- Running SLA Validation Scenarios ---"
pytest tests/sla/ -v

# 5. Run Performance Tests (optional, can be slow)
if [ "$RUN_PERFORMANCE_TESTS" = "true" ]; then
    echo "--- Running Performance Tests ---"
    pytest tests/performance/ -v -m "not soak"
    
    if [ "$RUN_SOAK_TESTS" = "true" ]; then
        echo "--- Running Soak Tests (Long Running) ---"
        pytest tests/performance/ -v -m soak
    fi
else
    echo "--- Skipping Performance Tests (set RUN_PERFORMANCE_TESTS=true to run) ---"
fi

echo "Test suite completed successfully!"
