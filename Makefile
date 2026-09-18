.PHONY: install run seed test docker-up docker-down clean

install: ## Install dependencies
	pip install -r requirements.txt

run: ## Run the full-stack app (API + UI) with auto-reload
	uvicorn backend.app.main:app --reload --port 8000

seed: ## (Re)seed demo data (runs automatically on first launch too)
	python -c "from backend.app.db.init_db import init_db; init_db()"

test: ## Run the test suite
	pytest backend/tests -q

docker-up: ## Run with Docker Compose
	docker compose up --build

ollama-up: ## Run app + free local LLM (Ollama) with Docker
	docker compose --profile ollama up --build

ollama-pull: ## Download llama3.1 into the Ollama container (one-time)
	docker compose exec ollama ollama pull llama3.1

docker-down: ## Stop Docker Compose
	docker compose down

clean: ## Remove local database and caches
	rm -f quicksave.db
	rm -rf __pycache__ backend/__pycache__ .pytest_cache
