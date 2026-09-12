# Issue 17 pilot evidence

This is a compact, sanitized record for the review unit. It contains no
model transcripts, credentials, tracker objects, or binary Inspect logs.

## Revisions and configuration

- shared base: `3ad2f8c24ce9e3d65128d45f87b4e294610b4d12`
- PR18 evidence head used: `d74071b87b55c7c3ceac88d983d86ad704740ed8`
- PR19 workflow implementation commit: `128864f94bc6d796fb5e6261558743175c0154ba`
  (historical implementation commit; the follow-up is recorded below)
- PR19 acceptance-control follow-up: `8237822c0de356f9c7597da331db1edc9fffce4f`
  (current branch head for this follow-up)
- evaluator: Inspect `0.3.259`, local sandbox, runner-owned contract diagnostics
  and one native local-repair task
- native model configuration when applicable: `gpt-5.6-luna`, reasoning effort
  `max`, finite command timeout; native candidate and baseline use the same
  task, tools, permissions, and budget
- comparison arms are selected explicitly by `workflows(arm=...)`; baseline
  requires its own skill-root and global-instruction paths. The no-catalog arm
  is only `no-catalog-diagnostic` with `with_skills=False`.

## Evaluator contract checks (not product verification)

| Command | Repetitions | Result |
|---|---:|---|
| `./scripts/validate-skills.sh` | 1 | 21 skills, 21 behavior cases, 6 routing cases, 21 workflow cases validated |
| `uv run python -m unittest evals.tests.test_workflows` | 1 | 16/16 passed, including runner-owned acceptance controls |
| `uv run python -m unittest discover -s evals/tests -p 'test_*.py'` | 1 | 53/53 passed on the combined stack |
| `uv run inspect eval evals/skills.py@evidence_smoke --max-samples 1` | 1 | contract lifecycle/evidence checks passed; intentional candidate error preserved |
| `uv run inspect eval evals/skills.py@workspace_baseline_lifecycle_smoke --max-samples 2` | 1 | contract check passed; invalid baseline skipped, valid baseline launched |
| `uv run inspect eval evals/skills.py@workspace_policy_smoke --max-samples 1` | 1 | contract check passed |
| `uv run inspect eval evals/skills.py@workspace_stat_cache_smoke --max-samples 1` | 1 | contract check passed |
| `uv run inspect eval evals/skills.py@workflow_fixture_smoke --max-samples 1` | 1 | evaluator-contract check passed |
| `uv run inspect eval evals/skills.py@workflow_failed_outcome_smoke --max-samples 1` | 1 | supported local contract rejected the intentionally failing outcome through the runner-owned acceptance regression (workspace 1.000, outcome 0.000) |
| `uv run inspect eval evals/skills.py@workflow_fixture_pilot --max-samples 7` | 1 | current seven-case evaluator-contract diagnostics completed (workspace/effects 1.000; not product verification) |
| `uv run inspect list tasks evals/skills.py` | 1 | 11 task entry points discovered; discovery only |

The follow-up also ran `uv sync --frozen`, `uv run python scripts/validate_catalog.py`,
`uv run inspect list tasks evals/skills.py`, and the installed CLI startup probe
with `codex exec --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check
--sandbox read-only --model gpt-5.6-luna -c 'model_reasoning_effort="max"'`;
the probe returned `STARTUP_OK`. `uv run python -m compileall -q
evals/skills.py evals/tests/test_workflows.py` passed. The optional `ruff`
check was attempted but is unavailable in this environment (`ruff` executable
and Python module are not installed), so no lint result is claimed.

Execution-ready case IDs:
`workflow-investigate-create-issue`, `workflow-draft-issue`,
`workflow-fix-open-draft-pr`, `workflow-native-local-repair`,
`workflow-custom-temporary`, `workflow-parallel-safe`, and
`workflow-correction-resume`.

The remaining fourteen cases are explicitly `routing-only`; their runtime
effects are unmeasured until executable inputs and an authorized application
are supplied. The fake tracker is a local evaluator contract fixture, not live
GitHub/GitLab publication. None of the rows above is used as evidence that an
agent, tracker, or product works; no fake or mocked result is counted as
verification.

## Native comparison pilot

The supported native case is deliberately narrower than the original
publication-shaped workflows: `workflow-native-local-repair` asks the agent to
repair the supplied tenant filter and run the supplied native regression. It
has no external-service deliverable, so the scorer can observe the complete
local outcome (edited source plus test result). The other six execution-ready
cases retain their original forbidden-effects lists. Their required external
effects are not observed by this local runner and are blocked before model
execution; they are not agent failures or successes.

The isolated startup check used the installed CLI with user configuration and
rules ignored:

```text
codex exec --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check \
  --sandbox read-only --model gpt-5.6-luna \
  -c 'model_reasoning_effort="max"' --json ...
→ STARTUP_OK (exit 0; no MCP/auth wait)
```

Both arms then used Inspect `0.3.259`, the same case/input, local sandbox,
`none/none` as the Inspect framework model (the solver invokes the native CLI),
`gpt-5.6-luna` at `max`, one epoch, one subprocess/sandbox, and the same finite
1800-second native command bound. The baseline was a detached checkout of the
last accepted revision `3ad2f8c24ce9e3d65128d45f87b4e294610b4d12` with its own
skills and global instructions; the candidate used the current PR19 roots.

| Arm | Supported attempts | Blocked cases | Local outcome | Native quality grade | Wall time |
|---|---:|---:|---|---:|---:|
| candidate | 1 | 6 | pass (workspace + `python test_bug.py`) | 4/4 | 179.6s |
| last accepted baseline | 1 | 6 | pass (workspace + `python test_bug.py`) | 3/4 | 151.6s |

This one-repetition pilot is not a superiority claim. The candidate scored 4/4
and the baseline 3/4 on the isolated native quality grader, but that difference
is not general evidence: the baseline response overstated its final diff after
leaving an untracked Python cache, and the candidate's response also included
failed exploratory commands. Both completed the local outcome checks. The
native CLI reported candidate usage of 433,788 input (397,056 cached) / 6,891
output / 3,658 reasoning tokens and baseline usage of 204,286 input (171,520
cached) / 5,050 output / 2,776 reasoning tokens. The isolated native graders
reported candidate usage of 21,267 input (8,960 cached) / 1,098 output / 1,034
reasoning tokens and baseline usage of 16,767 input / 1,474 output / 1,398
reasoning tokens. Inspect's aggregate `model_usage` is empty because the
nested CLI is outside its model accounting; the scorer preserves the nested
native and grader usage in sample metadata. Tool-call counts were 24 candidate
/ 15 baseline, with 3 failed commands in each arm (expected pre-fix
reproduction plus malformed exploratory commands). These counts are
observational, not a cost quote; no price telemetry was available.

The candidate and baseline both completed the local repair before corrective
user prompting. The candidate's final workspace evidence contained the
intended `bug.py` change. The baseline final evidence contained an additional
untracked `__pycache__` artifact, which the grader used to lower its quality
score; both final outcome checks nevertheless passed.
No external tracker, PR, merge, deployment, browser, or adversarial claim is
made from this local task. More repetitions and unseen task variants remain
unmeasured.

The final boundary-control run selected the six non-native execution-ready IDs
(`workflow-investigate-create-issue`, `workflow-draft-issue`,
`workflow-fix-open-draft-pr`, `workflow-custom-temporary`,
`workflow-parallel-safe`, and `workflow-correction-resume`) with one epoch and
`--no-fail-on-error --score-on-error`. All six returned
`workflow_support_status=blocked` and `candidate_skipped=true`; no native model
was launched and all three outcome scorers were unscored with
`acceptance_blocked=true`. The reasons identify the unobserved tracker,
publication, merge, deployment, or production boundaries. This is a blocked
configuration count, not six agent failures.

## Follow-up native comparison (acceptance repair)

At `8237822c0de356f9c7597da331db1edc9fffce4f`, both explicit catalog arms ran
only `workflow-native-local-repair` with the same current evaluator/scorer,
runner-controlled original acceptance script, local sandbox, `gpt-5.6-luna`
at max reasoning, one epoch, one sample, one model connection, subprocess,
and sandbox, and the same finite 1800-second nested command bound. The
candidate selected the current PR19 skill/global roots; the baseline selected
the last accepted catalog/global roots at `3ad2f8c24ce9e3d65128d45f87b4e294610b4d12`.
No candidate instructions were supplied to the baseline arm.

| Arm | Attempts | Blocked cases | Workspace/effect outcome | Native quality | Time | Native usage (input/output/reasoning) | Tool calls / failed |
|---|---:|---:|---|---:|---:|---|---:|
| candidate | 1 | 6 | 1.000 / 1.000 | 4/4 | 161.449s | 506,291 / 5,522 / 2,962 | 25 / 1 |
| last accepted baseline | 1 | 6 | 1.000 / 1.000 | 4/4 | 110.713s | 219,997 / 3,709 / 2,017 | 9 / 2 |

Both agents completed the repair before any corrective user prompting. The
runner acceptance check passed the corrected implementation and would reject
the unchanged implementation even if `test_bug.py` were replaced; the unit
regressions exercise those three real subprocess cases. This one-repetition
comparison is a tie, not evidence of superiority. Grader usage was
candidate `22,340` input / `799` output / `737` reasoning and baseline `15,996`
input / `426` output / `361` reasoning. Inspect aggregate model usage remains
empty because the nested CLI is outside its accounting. No price telemetry was
available. Six other execution-ready cases remained blocked before native
launch because their required external effects are outside the observed
boundary; they are not agent failures.

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

The real `pallets/markupsafe` checkout remains a repository-native baseline
only; no agent repair was requested against it in this pilot. Live tracker or
product/browser behavior, publication, deployment, adversarial execution, and
production behavior remain unmeasured or unsupported. The six blocked workflow
cases remain contract diagnostics, not validation. The native comparison has
one repeated pair and therefore cannot establish general reliability or a
quality/cost win.
