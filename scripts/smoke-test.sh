#!/usr/bin/env bash
set -euo pipefail

PORT="${SMOKE_PORT:-18093}"
SKILLS_DIR="$(mktemp -d)"
LOG_FILE="$(mktemp)"
PID_FILE="$(mktemp)"
FAILED=0

cleanup() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        kill "$(cat "$PID_FILE")" 2>/dev/null || true
        wait "$(cat "$PID_FILE")" 2>/dev/null || true
    fi
    rm -rf "$SKILLS_DIR" "$LOG_FILE" "$PID_FILE"
}
trap cleanup EXIT

check_endpoint() {
    local url="http://localhost:${PORT}$1"
    local label="$2"
    if curl -sf "$url" >/dev/null 2>&1; then
        echo "  [OK] $label"
    else
        echo "  [FAIL] $label"
        FAILED=1
    fi
}

echo "Smoke test: starting gateway on port ${PORT}..."
AUTH_MODE=dev-none SKILLS_DIR="$SKILLS_DIR" PORT="$PORT" uv run skills-gateway run >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
sleep 3

if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "ERROR: Gateway failed to start. Logs:"
    cat "$LOG_FILE"
    exit 1
fi

check_endpoint "/health"    "health"
check_endpoint "/ready"     "ready"
check_endpoint "/version"   "version"
check_endpoint "/inventory" "inventory"
check_endpoint "/metrics"   "metrics"

echo "Smoke test logs (last 10 lines):"
tail -10 "$LOG_FILE"

if [ "$FAILED" -ne 0 ]; then
    echo "Smoke test FAILED"
    exit 1
fi

echo "Smoke test PASSED"