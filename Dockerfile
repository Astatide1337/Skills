FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

COPY --from=ghcr.io/astral-sh/uv:0.9.17@sha256:5cb6b54d2bc3fe2eb9a8483db958a0b9eebf9edff68adedb369df8e7b98711a2 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY server.py ./
COPY catalog.yaml ./
COPY skills/ /skills/
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 --create-home appuser \
    && chown -R appuser:appuser /app /skills

ENV PATH=/app/.venv/bin:$PATH

USER appuser
EXPOSE 8091

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8091/health', timeout=3)"

CMD ["opentelemetry-instrument", "python", "server.py"]
