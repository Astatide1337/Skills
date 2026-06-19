.PHONY: test smoke verify build run lint compile

compile:
	uv run python -m compileall .

lint:
	uv run python -m compileall .
	uv run pytest tests/ -q

test:
	uv run pytest tests/ -v

smoke:
	@echo "Smoke test: starting gateway in background..."
	@AUTH_MODE=dev-none SKILLS_DIR=$(HOME)/skills uv run skills-gateway run &
	@sleep 3
	@curl -sf http://localhost:8091/health && echo " [health OK]"
	@curl -sf http://localhost:8091/ready && echo " [ready OK]"
	@curl -sf http://localhost:8091/version && echo " [version OK]"
	@curl -sf http://localhost:8091/inventory && echo " [inventory OK]"
	@curl -sf http://localhost:8091/metrics && echo " [metrics OK]"
	@kill %1 2>/dev/null || true

verify: compile test

build:
	docker compose build

run:
	uv run skills-gateway run

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f
