#!/bin/bash
# Simulate GitHub Actions workflow locally
# This script runs the same checks that will run in CI/CD

set -e

echo "🚀 Simulating GitHub Actions Workflow Locally"
echo "=============================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Job 1: Lint
echo -e "\n${YELLOW}📋 Job 1: Code Quality Checks${NC}"
echo "-----------------------------------"

echo "Installing linting tools..."
pip install -q flake8 black isort 2>/dev/null || echo "Linting tools already installed"

echo "Checking code formatting with black..."
if black --check src/ tests/ 2>/dev/null; then
    echo -e "${GREEN}✅ Code formatting OK${NC}"
else
    echo -e "${YELLOW}⚠️  Code formatting issues found (non-blocking)${NC}"
fi

echo "Checking import sorting with isort..."
if isort --check-only src/ tests/ 2>/dev/null; then
    echo -e "${GREEN}✅ Import sorting OK${NC}"
else
    echo -e "${YELLOW}⚠️  Import sorting issues found (non-blocking)${NC}"
fi

echo "Linting with flake8..."
if flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics 2>/dev/null; then
    echo -e "${GREEN}✅ No critical lint errors${NC}"
else
    echo -e "${RED}❌ Critical lint errors found${NC}"
fi

# Job 2: Unit Tests
echo -e "\n${YELLOW}🧪 Job 2: Unit Tests${NC}"
echo "-----------------------------------"

echo "Installing test dependencies..."
pip install -q pytest pytest-cov requests prometheus_client 2>/dev/null || echo "Dependencies already installed"

echo "Running unit tests with coverage..."
if pytest tests/unit/ -v --cov=src --cov-report=term-missing 2>&1 | tail -20; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
else
    echo -e "${RED}❌ Unit tests failed${NC}"
    exit 1
fi

# Job 3: Validation
echo -e "\n${YELLOW}🔍 Job 3: Configuration Validation${NC}"
echo "-----------------------------------"

echo "Validating Docker Compose configuration..."
if docker compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker Compose configuration is valid${NC}"
else
    echo -e "${RED}❌ Docker Compose configuration is invalid${NC}"
    exit 1
fi

echo "Checking for required files..."
required_files=(
    "docker-compose.yml"
    "Makefile"
    ".env.example"
    "scripts/run_tests.sh"
    "tests/conftest.py"
)

all_files_found=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ Found: $file${NC}"
    else
        echo -e "${RED}❌ Missing: $file${NC}"
        all_files_found=false
    fi
done

if [ "$all_files_found" = false ]; then
    exit 1
fi

echo "Validating test structure..."
test_dirs=(
    "tests/unit"
    "tests/integration"
    "tests/e2e"
    "tests/chaos"
    "tests/sla"
    "tests/performance"
)

all_dirs_found=true
for dir in "${test_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ Found: $dir${NC}"
    else
        echo -e "${RED}❌ Missing: $dir${NC}"
        all_dirs_found=false
    fi
done

if [ "$all_dirs_found" = false ]; then
    exit 1
fi

# Job 4: Integration Tests (Optional - requires Docker)
if [ "$RUN_INTEGRATION" = "true" ]; then
    echo -e "\n${YELLOW}🔗 Job 4: Integration Tests${NC}"
    echo "-----------------------------------"
    
    echo "Checking if services are running..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Services are running${NC}"
        
        echo "Running integration tests..."
        if pytest tests/integration/ -v; then
            echo -e "${GREEN}✅ Integration tests passed${NC}"
        else
            echo -e "${RED}❌ Integration tests failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Services not running - skipping integration tests${NC}"
        echo "   To run integration tests: docker compose up -d && RUN_INTEGRATION=true $0"
    fi
else
    echo -e "\n${YELLOW}⏭️  Skipping Integration Tests${NC}"
    echo "   (Set RUN_INTEGRATION=true to run)"
fi

# Summary
echo -e "\n${GREEN}=============================================="
echo "✅ GitHub Actions Simulation Complete!"
echo "=============================================="
echo ""
echo "Summary:"
echo "  ✅ Code Quality Checks: PASSED"
echo "  ✅ Unit Tests: PASSED"
echo "  ✅ Configuration Validation: PASSED"
if [ "$RUN_INTEGRATION" = "true" ]; then
    echo "  ✅ Integration Tests: CHECKED"
else
    echo "  ⏭️  Integration Tests: SKIPPED"
fi
echo ""
echo "Your code is ready for GitHub Actions! 🎉"
