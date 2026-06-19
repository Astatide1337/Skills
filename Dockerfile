ARG SKG_COMMIT=unknown
ARG SKG_BUILD_TIME=unknown

FROM python:3.12-slim

ARG SKG_COMMIT
ARG SKG_BUILD_TIME

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY server.py ./
COPY skills_gateway/ ./skills_gateway/

ENV SKILLS_DIR=/skills
ENV PATH="/app/.venv/bin:$PATH"
ENV SKG_BUILD_COMMIT=${SKG_COMMIT}
ENV SKG_BUILD_TIME=${SKG_BUILD_TIME}

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8091

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8091/health || exit 1

CMD ["skills-gateway", "run"]
