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
	@AUTH_MODE=dev-none SKILLS_DIR=$$(mktemp -d) uv run skills-gateway run & \
	PID=$$!; \
	sleep 3; \
	S=0; \
	curl -sf http://localhost:8091/health && echo " [health OK]" || S=1; \
	curl -sf http://localhost:8091/ready && echo " [ready OK]" || S=1; \
	curl -sf http://localhost:8091/version && echo " [version OK]" || S=1; \
	curl -sf http://localhost:8091/inventory && echo " [inventory OK]" || S=1; \
	curl -sf http://localhost:8091/metrics && echo " [metrics OK]" || S=1; \
	kill $$PID 2>/dev/null || true; \
	wait $$PID 2>/dev/null || true; \
	exit $$S

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
