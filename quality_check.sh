#!/bin/bash
set -e

echo "Running code quality checks..."
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
FORMAT=false
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --format)
            FORMAT=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--format] [--check-only]"
            echo "  --format: Run black formatter"
            echo "  --check-only: Only check formatting without modifying files"
            exit 1
            ;;
    esac
done

# Function to run a check
run_check() {
    local name=$1
    local command=$2

    echo -e "${YELLOW}Running $name...${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        echo ""
        return 1
    fi
}

# Track failures
FAILED=0

# Run black formatter or check
if [ "$FORMAT" = true ]; then
    run_check "Black (formatting)" "uv run black backend/ main.py" || FAILED=$((FAILED + 1))
elif [ "$CHECK_ONLY" = true ]; then
    run_check "Black (check only)" "uv run black --check backend/ main.py" || FAILED=$((FAILED + 1))
fi

# Run ruff linter
run_check "Ruff (linting)" "uv run ruff check backend/ main.py" || FAILED=$((FAILED + 1))

# Run mypy type checker
run_check "MyPy (type checking)" "uv run mypy backend/ main.py" || FAILED=$((FAILED + 1))

# Run tests
run_check "Pytest (tests)" "uv run pytest" || FAILED=$((FAILED + 1))

# Summary
echo "================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED check(s) failed${NC}"
    exit 1
fi
