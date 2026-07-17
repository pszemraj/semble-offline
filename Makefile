PYTHON ?= python

.PHONY: help install test test-no-git lint typecheck format check build verify-wheel

help:
	@echo "Available targets:"
	@echo "  install       Install the project and development dependencies"
	@echo "  test          Run the test suite"
	@echo "  test-no-git   Run tests except remote Git integration tests"
	@echo "  lint          Run lint, formatting, and docstring checks"
	@echo "  typecheck     Run mypy"
	@echo "  format        Apply Ruff fixes and formatting"
	@echo "  check         Run tests, lint, and type checking"
	@echo "  build         Build the wheel for the staged platform bundle"
	@echo "  verify-wheel  Verify the built release wheel"

install:
	$(PYTHON) -m pip install -e ".[dev,mcp]"

test:
	$(PYTHON) -m pytest

test-no-git:
	$(PYTHON) -m pytest --ignore=tests/test_git.py

lint:
	$(PYTHON) -m ruff check src tests scripts setup.py
	$(PYTHON) -m ruff format --check src tests scripts setup.py
	pydoclint src

typecheck:
	$(PYTHON) -m mypy src

format:
	$(PYTHON) -m ruff check --fix src tests scripts setup.py
	$(PYTHON) -m ruff format src tests scripts setup.py

check: test lint typecheck

build:
	$(PYTHON) -m build --wheel

verify-wheel:
	$(PYTHON) scripts/verify_wheel.py dist/semble-0.5.1+offline.2-py3-none-manylinux_2_34_x86_64.whl
