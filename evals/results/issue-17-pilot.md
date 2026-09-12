# Issue 17 pilot evidence

This is a compact, sanitized record for the review unit. It contains no
model transcripts, credentials, tracker objects, or binary Inspect logs.

## Revisions and configuration

- shared base: `3ad2f8c24ce9e3d65128d45f87b4e294610b4d12`
- PR18 evidence head used: `d74071b87b55c7c3ceac88d983d86ad704740ed8`
- PR19 workflow head after this unit: `32921ad40a740d361e3d3219b3fd410b9164c75b`
- evaluator: Inspect `0.3.259`, local sandbox, no-model smoke tasks
- native model configuration when applicable: `gpt-5.6-luna`, reasoning effort
  `max`, finite command timeout; native candidate and baseline use the same
  task, tools, permissions, and budget
- comparison arms are selected explicitly by `workflows(arm=...)`; baseline
  requires its own skill-root and global-instruction paths. The no-catalog arm
  is only `no-catalog-diagnostic` with `with_skills=False`.

## Evaluator contract checks (not product verification)

| Command | Repetitions | Result |
|---|---:|---|
| `./scripts/validate-skills.sh` | 1 | 21 skills, 21 behavior cases, 6 routing cases, 20 workflow cases validated |
| `uv run python -m unittest discover -s evals/tests -p 'test_*.py'` | 1 | 43/43 passed on the combined stack |
| `uv run inspect eval evals/skills.py@evidence_smoke --max-samples 1` | 1 | contract lifecycle/evidence checks passed; intentional candidate error preserved |
| `uv run inspect eval evals/skills.py@workspace_baseline_lifecycle_smoke --max-samples 2` | 1 | contract check passed; invalid baseline skipped, valid baseline launched |
| `uv run inspect eval evals/skills.py@workspace_policy_smoke --max-samples 1` | 1 | contract check passed |
| `uv run inspect eval evals/skills.py@workspace_stat_cache_smoke --max-samples 1` | 1 | contract check passed |
| `uv run inspect eval evals/skills.py@workflow_fixture_smoke --max-samples 1` | 1 | evaluator-contract check passed |
| `uv run inspect eval evals/skills.py@workflow_fixture_pilot --max-samples 6` | 1 | evaluator-contract checks passed across six execution-ready cases |

Execution-ready case IDs:
`workflow-investigate-create-issue`, `workflow-draft-issue`,
`workflow-fix-open-draft-pr`, `workflow-custom-temporary`,
`workflow-parallel-safe`, and `workflow-correction-resume`.

The remaining fourteen cases are explicitly `routing-only`; their runtime
effects are unmeasured until executable inputs and an authorized application
are supplied. The fake tracker is a local evaluator contract fixture, not live
GitHub/GitLab publication. None of the rows above is used as evidence that an
agent, tracker, or product works; no fake or mocked result is counted as
verification.

## Real repository evidence

An explicitly authorized public checkout was used instead of a synthetic
application: [pallets/markupsafe](https://github.com/pallets/markupsafe) at
`b2e4d9c7687be25695fffbe93a37622302b24fb1`. Its repository-native commands
were run without source changes:

| Command | Result |
|---|---|
| `uv run --project /tmp/skills-real-demo.aUsdnu pytest -q` | 79 passed, 1 skipped |
| `uv run --project /tmp/skills-real-demo.aUsdnu ruff check` | all checks passed |
| `uv run --project /tmp/skills-real-demo.aUsdnu mypy` | no issues in 10 source files |
| `git -C /tmp/skills-real-demo.aUsdnu diff --exit-code` | clean |

This proves only the pinned checkout's native tests and static checks. It does
not prove a live publication, deployment, browser flow, or improved agent
behavior.

## Limits

No native comparison pilot is claimed by this record. A Luna/max read-only
agent attempt against the real checkout was stopped after it stalled in an
external tool/authentication wait; no score was recorded. Live tracker or
product/browser behavior, adversarial execution, and production behavior remain
unmeasured or unsupported. The six fixture cases remain contract diagnostics,
not validation.
