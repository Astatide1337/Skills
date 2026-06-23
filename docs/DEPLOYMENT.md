# Deployment

## Local Development

```bash
# Install dependencies
uv sync

# Run with dev auth
AUTH_MODE=dev-none SKILLS_DIR=~/skills uv run skills-gateway run
```

## Docker Compose

```bash
# REQUIRED: Copy and edit env file before first run
cp .env.example .env
# Edit .env with your settings (at minimum, set AUTH_MODE)

# Build and start
docker compose up -d --build

# Check health
curl http://localhost:8091/health
curl http://localhost:8091/ready

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Docker Run (without Compose)

```bash
docker build \
  --build-arg SKG_COMMIT=$(git rev-parse --short HEAD) \
  --build-arg SKG_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t skills-gateway .

docker run -d \
  -p 8091:8091 \
  -v /path/to/skills:/skills:ro \
  --env-file .env \
  --name skills-gateway \
  skills-gateway
```

## Environment Variables

See [CONFIG.md](CONFIG.md) for the full list of environment variables.

## Health Monitoring

The Docker Compose file includes a healthcheck:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
  interval: 30s
  timeout: 5s
  start_period: 10s
  retries: 3
```

You can also check readiness:

```bash
curl http://localhost:8091/ready
```

## Build-Time Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SKG_COMMIT` | Git commit hash | `unknown` |
| `SKG_BUILD_TIME` | Build timestamp | `unknown` |

These are exposed via the `/version` endpoint.
