# E2E Test Report

**Date:** 2026-06-19
**Auth Mode:** dev-none
**Skills Dir:** /tmp/e2e-skills (1 valid skill: echo-skill)
**Port:** 18091

## Endpoint Results

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/health` | 200 | `{"status":"alive"}` |
| `/ready` | 200 | All checks pass: skills_dir, skills_scan, auth_config |
| `/version` | 200 | `{"version":"0.1.0","commit":"unknown","build_time":"unknown"}` |
| `/inventory` | 200 | 1 skill, 4 tools, auth_mode=dev-none |
| `/metrics` | 200 | Prometheus text format, skills_gateway_up=1, skills_gateway_ready=1 |
| `/docs` | 200 | Links to all doc endpoints |
| `/docs/config` | 200 | Full config dump (no secrets) |
| `/docs/profiles` | 200 | Empty profiles dict |
| `/docs/catalogs` | 200 | Empty catalogs dict |
| `/docs/auth` | 200 | `{"mode":"dev-none","internal_bypass":false}` |

## All Endpoints Passing

All 10 HTTP endpoints return 200 with expected JSON bodies. No errors in gateway output.

## Test Suite

94 tests passing across:
- test_config.py (22 tests)
- test_cli.py (8 tests)
- test_skills.py (12 tests)
- test_skills_extra.py (14 tests)
- test_endpoints.py (12 tests)
- test_logging.py (10 tests)
- test_metrics.py (6 tests)
- test_auth.py (9 tests)

## Docker Compose

Not yet verified (requires Docker daemon). See DEPLOYMENT.md for instructions.
