.PHONY: install test lint format typecheck run clean help dev-setup

help:
	@echo "Available targets:"
	@echo "  install     - Install all dependencies"
	@echo "  dev-setup   - Set up development environment"
	@echo "  test        - Run tests with coverage"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with ruff"
	@echo "  typecheck   - Run mypy type checking"
	@echo "  run         - Run the orchestrator API locally"
	@echo "  clean       - Clean build artifacts and caches"

install:
	pip install -e ".[dev]"

dev-setup: install
	pre-commit install
	cp .env.example .env
	docker compose -f infra/docker/docker-compose.yml up -d postgres redis temporal
	@echo "Waiting for services to be ready..."
	sleep 5
	alembic upgrade head
	python scripts/seed_demo_data.py

test:
	pytest

lint:
	ruff check .
	mypy .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy .

run:
	uvicorn apps.orchestrator.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ htmlcov/ .coverage
