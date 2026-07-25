.PHONY: help install dev test lint type-check run consumer docker-up docker-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

dev: ## Install dev dependencies and set up pre-commit
	pip install -r requirements.txt
	pip install ruff mypy pre-commit
	pre-commit install

test: ## Run tests with coverage
	pytest tests/ -v --cov=src --cov-report=term-missing

lint: ## Run linter
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Auto-format code
	ruff format src/ tests/

type-check: ## Run type checker
	mypy src/ --ignore-missing-imports

run: ## Run the API server
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

consumer: ## Run the Kafka consumer
	python -m src.pipeline.consumer

docker-up: ## Start all services with Docker Compose
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## View logs for all services
	docker compose logs -f

benchmark: ## Run model benchmark against gold set
	python -m src.training.benchmark --gold-set data/gold.parquet

train: ## Trigger model retraining
	python -m src.training.trainer

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
