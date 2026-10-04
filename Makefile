.PHONY: install run run-prod seed test docker-up docker-down docker-prod clean deploy-check

install: ## Install dependencies
	pip install -r requirements.txt

run: ## Run the full-stack app (API + UI) with auto-reload
	uvicorn backend.app.main:app --reload --port 8000

run-prod: ## Run in production mode (no reload, proxy headers, honors $PORT)
	PORT=$${PORT:-8000} uvicorn backend.app.main:app --host 0.0.0.0 --port $${PORT:-8000} --proxy-headers

seed: ## (Re)seed demo data (runs automatically on first launch too)
	python -c "from backend.app.db.init_db import init_db; init_db()"

test: ## Run the test suite
	pytest backend/tests -q

deploy-check: ## Verify app is deployment-ready (tests + health import + dockerfile exists)
	@echo "🔍 Checking deployment readiness..."
	@test -f backend/Dockerfile || (echo "❌ backend/Dockerfile missing" && exit 1)
	@test -f Dockerfile || (echo "❌ Root Dockerfile missing" && exit 1)
	@test -f render.yaml || (echo "❌ render.yaml missing" && exit 1)
	@test -f railway.json || (echo "❌ railway.json missing" && exit 1)
	@test -f Procfile || (echo "❌ Procfile missing" && exit 1)
	@pytest backend/tests -q
	@echo "✅ All deployment checks passed!"

docker-up: ## Run with Docker Compose (dev)
	docker compose up --build

docker-prod: ## Run Docker in prod mode with persistent volume
	docker compose up --build -d && docker compose logs -f

ollama-up: ## Run app + free local LLM (Ollama) with Docker
	docker compose --profile ollama up --build

ollama-pull: ## Download llama3.1 into the Ollama container (one-time)
	docker compose exec ollama ollama pull llama3.1

docker-down: ## Stop Docker Compose
	docker compose down

clean: ## Remove local database and caches
	rm -f quicksave.db
	rm -rf __pycache__ backend/__pycache__ .pytest_cache
	rm -rf data/*.db data/*.db-journal 2>/dev/null || true
