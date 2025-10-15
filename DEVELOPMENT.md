# Development Guide

## Code Quality Tools

This project uses several code quality tools to maintain consistent code style and catch potential issues:

- **Black**: Automatic code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pytest**: Testing framework

## Quick Start

### Install Development Dependencies

```bash
uv sync --group dev
```

### Format Code

```bash
./format.sh
```

Or manually:
```bash
uv run black backend/ main.py
```

### Run All Quality Checks

```bash
./quality_check.sh
```

This will run:
1. Ruff linting
2. MyPy type checking
3. Pytest tests

### Format Code During Quality Check

```bash
./quality_check.sh --format
```

### Check Formatting Without Modifying Files

```bash
./quality_check.sh --check-only
```

## Individual Tool Commands

### Black (Formatting)
```bash
# Format code
uv run black backend/ main.py

# Check formatting without changes
uv run black --check backend/ main.py
```

### Ruff (Linting)
```bash
# Run linter
uv run ruff check backend/ main.py

# Auto-fix issues
uv run ruff check --fix backend/ main.py
```

### MyPy (Type Checking)
```bash
# Run type checker
uv run mypy backend/ main.py
```

### Pytest (Testing)
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest backend/tests/test_specific.py
```

## Configuration

All tool configurations are in `pyproject.toml`:

- **Black**: 88 character line length, Python 3.13 target
- **Ruff**: Checks for errors, potential bugs, import sorting, and modern Python idioms
- **MyPy**: Basic type checking with Python 3.13 compatibility

## Pre-commit Workflow

Before committing code, run:

```bash
./quality_check.sh --format
```

This ensures your code is properly formatted and passes all quality checks.
