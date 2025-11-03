.PHONY: help install migrate migrate-down migrate-create dev test docker-build docker-run docker-compose-up docker-compose-down clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies with Poetry
	poetry install

migrate:  ## Run database migrations (upgrade to latest)
	poetry run alembic upgrade head

migrate-down:  ## Rollback last migration
	poetry run alembic downgrade -1

migrate-create:  ## Create new migration (use: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG is required. Usage: make migrate-create MSG='your migration message'"; \
		exit 1; \
	fi
	poetry run alembic revision --autogenerate -m "$(MSG)"

dev:  ## Run application in development mode
	ENVIRONMENT=dev PYTHONPATH=src poetry run python -m main

test:  ## Run tests with coverage
	PYTHONPATH=src poetry run pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

docker-build:  ## Build Docker image
	docker build -t alert-manager:latest .

docker-run:  ## Run Docker container
	docker run --env-file .env --name alert-manager -d alert-manager:latest

docker-compose-up:  ## Start with docker-compose (includes PostgreSQL)
	docker-compose up -d

docker-compose-down:  ## Stop docker-compose services
	docker-compose down

docker-compose-logs:  ## View docker-compose logs
	docker-compose logs -f

clean:  ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov dist build

generate-key:  ## Generate encryption key
	@python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
