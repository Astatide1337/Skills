# Issue 17 pilot evidence

This is a compact, sanitized record for the review unit. It contains no
model transcripts, credentials, tracker objects, or binary Inspect logs.

## Revisions and configuration

- shared base: `3ad2f8c24ce9e3d65128d45f87b4e294610b4d12`
- PR18 evidence head used: `d74071b87b55c7c3ceac88d983d86ad704740ed8`
- PR19 workflow head before this unit: `21f840fbf0c3baa658352d3230c403257ca9f8d4`
- evaluator: Inspect `0.3.259`, local sandbox, no-model smoke tasks
- native model configuration when applicable: `gpt-5.6-luna`, reasoning effort
  `max`, finite command timeout; native candidate and baseline use the same
  task, tools, permissions, and budget
- comparison arms are selected explicitly by `workflows(arm=...)`; baseline
  requires its own skill-root and global-instruction paths. The no-catalog arm
  is only `no-catalog-diagnostic` with `with_skills=False`.

## Deterministic checks

| Command | Repetitions | Result |
|---|---:|---|
| `./scripts/validate-skills.sh` | 1 | 21 skills, 21 behavior cases, 6 routing cases, 20 workflow cases validated |
| `uv run python -m unittest discover -s evals/tests -p 'test_*.py'` | 1 | 39/39 passed on the combined temporary stack |
| `uv run inspect eval evals/skills.py@evidence_smoke --max-samples 1` | 1 | workspace policy/evidence 1.000; candidate error intentionally preserved |
| `uv run inspect eval evals/skills.py@workspace_baseline_lifecycle_smoke --max-samples 2` | 1 | 1.000; invalid baseline skipped, valid baseline launched |
| `uv run inspect eval evals/skills.py@workspace_policy_smoke --max-samples 1` | 1 | 1.000 |
| `uv run inspect eval evals/skills.py@workspace_stat_cache_smoke --max-samples 1` | 1 | 1.000 |
| `uv run inspect eval evals/skills.py@workflow_fixture_smoke --max-samples 1` | 1 | workspace policy/effects 1.000 |
| `uv run inspect eval evals/skills.py@workflow_fixture_pilot --max-samples 6` | 1 | workspace policy/effects 1.000 across six execution-ready cases |

Execution-ready case IDs:
`workflow-investigate-create-issue`, `workflow-draft-issue`,
`workflow-fix-open-draft-pr`, `workflow-custom-temporary`,
`workflow-parallel-safe`, and `workflow-correction-resume`.

The remaining fourteen cases are explicitly `routing-only`; their runtime
effects are unmeasured until executable inputs and an authorized application
are supplied. The fake tracker is a local fixture demonstration, not live
GitHub/GitLab publication.

## Limits

No native comparison pilot is claimed by this record. A live product/browser
demonstration, adversarial execution, and production behavior remain
unmeasured or unsupported; no empty fixture is counted as validation.
