.PHONY: test smoke verify build run lint compile

compile:
	uv run python -m compileall .

lint:
	uv run python -m compileall .
	uv run pytest tests/ -q

test:
	uv run pytest tests/ -v

smoke:
	bash scripts/smoke-test.sh

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
