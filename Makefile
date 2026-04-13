# Local Bank AI Agent - Makefile
# Common development tasks

.PHONY: help install test test-cov clean run run-dev docker-build docker-run docker-compose docker-down

# Default target
help:
	@echo "Local Bank AI Agent - Development Tasks"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install dependencies from requirements.txt"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-cov        Run tests with coverage report"
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
	@echo "  docker-down     Stop docker-compose services"

# Installation
install:
	pip install -r requirements.txt

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=. --cov-report=term-missing

# Development
run:
	python web_server.py

run-dev:
	uvicorn web_server:app --reload --host 0.0.0.0 --port 8000

clean:
	@if exist "__pycache__" rmdir /s /q __pycache__
	@if exist ".pytest_cache" rmdir /s /q .pytest_cache
	@if exist ".ruff_cache" rmdir /s /q .ruff_cache
	@if exist "htmlcov" rmdir /s /q htmlcov
	@if exist ".coverage" del /q .coverage
	@if exist ".mypy_cache" rmdir /s /q .mypy_cache

# Docker
docker-build:
	docker build -t local-bank-ai-agent:latest .

docker-run:
	docker run -p 8000:8000 \
		-v %CD%/credentials.json:/app/credentials.json:ro \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
		local-bank-ai-agent:latest

docker-compose:
	docker-compose up -d

docker-compose-logs:
	docker-compose logs -f app

docker-down:
	docker-compose down

docker-clean:
	docker rmi local-bank-ai-agent:latest || true
