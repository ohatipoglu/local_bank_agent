# Local Bank AI Agent - Makefile
# Common development tasks

.PHONY: help install dev-install test test-cov lint format clean run docker-build docker-run

# Default target
help:
	@echo "Local Bank AI Agent - Development Tasks"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install production dependencies"
	@echo "  dev-install     Install with development tools"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-cov        Run tests with coverage report"
	@echo "  test-html       Run tests and generate HTML coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run linters (ruff)"
	@echo "  lint-fix        Run linters and auto-fix issues"
	@echo "  format          Format code with black"
	@echo "  type-check      Run type checker (mypy)"
	@echo "  pre-commit      Install pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  run             Run the application"
	@echo "  run-dev         Run with reload mode"
	@echo "  clean           Remove build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build    Build Docker image"
	@echo "  docker-run      Run Docker container"
	@echo "  docker-compose  Start with docker-compose"
	@echo "  docker-clean    Remove Docker images"

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=70

test-html:
	pytest tests/ -v --cov=. --cov-report=html
	@echo "HTML coverage report generated in htmlcov/"
	@echo "Open: file://$(PWD)/htmlcov/index.html"

# Code Quality
lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	black .

type-check:
	mypy application core domain infrastructure

pre-commit:
	pre-commit install
	pre-commit run --all-files

# Development
run:
	python web_server.py

run-dev:
	uvicorn web_server:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.pyc" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .eggs/

# Docker
docker-build:
	docker build -t local-bank-ai-agent:latest .

docker-run:
	docker run -p 8000:8000 \
		-v $(PWD)/credentials.json:/app/credentials.json:ro \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		local-bank-ai-agent:latest

docker-compose:
	docker-compose up -d

docker-compose-logs:
	docker-compose logs -f app

docker-compose-down:
	docker-compose down

docker-clean:
	docker rmi local-bank-ai-agent:latest || true

# Quick development workflow
dev-setup: dev-install
	@echo ""
	@echo "Development setup complete!"
	@echo "Run 'make test' to verify installation"

# Check code quality
check: lint type-check test-cov
	@echo ""
	@echo "All checks passed!"

# Install git hooks
hooks:
	pre-commit install --install-hooks

# Generate requirements from pyproject.toml
requirements:
	pip-compile pyproject.toml -o requirements.txt

# View test coverage in browser
view-cov:
	python -m http.server --directory htmlcov 8080

# Run specific test file
test-file:
	@pytest $(file) -v

# Benchmark
benchmark:
	pytest tests/ -v --benchmark-only || echo "Benchmark tests not configured yet"
