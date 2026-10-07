# Evaluate behavior and overhead

Use when running or designing skill evaluations. Freeze the representative
request, expected observable behavior, authority, tools, candidate/baseline
instructions, model and effort, finite run budget and acceptance gates before
execution. Derive cases from observed failures; include ordinary tasks and
valid near-misses, not only adversarial traps. Reserve held-out cases before
choosing instruction changes. Repetitions are not independent tasks.

## Use existing Inspect tasks

The tasks in `evals/skills.py` run the locally authenticated Codex CLI in its
workspace sandbox. Personal configuration and unrelated installed skills are
excluded. Inspect owns execution, concurrency, logs, scorers and viewing.
Catalog behavior injects a selected skill verbatim; its no-skill baseline gets
neither guidance nor catalog. Workflows compare explicit catalog roots and
global instructions; a no-catalog diagnostic must be named as such. Test
installation/automatic routing separately from instruction efficacy.

First run `python scripts/namespace-doctor.py`, `codex login status` and
`uv run inspect list tasks evals/skills.py`. An unsupported namespace fails
honestly; never weaken isolation, replace integration with mocks or label the
unavailable run passed. Live model use requires user authorization.

Example bounded paired catalog runs:

```bash
uv run inspect eval evals/skills.py@catalog -T native_model=gpt-5.6-luna -T native_effort=medium -T grader_effort=high --limit 2 --epochs 2 --max-samples 2 --time-limit 480
uv run inspect eval evals/skills.py@catalog -T with_skills=false -T native_model=gpt-5.6-luna -T native_effort=medium -T grader_effort=high --limit 2 --epochs 2 --max-samples 2 --time-limit 480
```

Select representative sample IDs instead of the first two when appropriate.
`native_effort` applies to candidates and routing; `grader_effort` and optional
`grader_model` configure assessment separately. Defaults are `medium` for candidates/routing and `high` for grading;
use explicit `max` only for a justified comparison with historical runs. Supported effort names are low, medium, high, xhigh
and max; the chosen model may reject a level, which is a failed/unavailable run,
not permission to silently substitute a setting. Keep both arms identical and
the grader fixed while measuring an instruction change. Measure a different
effort as a separate experiment. Parent Inspect model settings and token/cost
limits do not account for the nested CLI; use explicit sample time budgets and
inspect native usage. Do not describe a time limit as a quota cap.

## Withhold evaluation cues

Give candidates organic requests and project-shaped files, not the rubric,
expected routes, comparison arm, reference answer or directions to recite
skills/principles. Use neutral temporary paths and task guidance. Retain the
real paths/digests and arm mapping privately in runner logs; blinding must not
rewrite the evidence or hide a failed check.

The native grader receives quoted task, target and runner evidence in a fresh
directory without the candidate's AGENTS file/catalog. Construction cases use
`artifact_first_review`: record an artifact assessment without the final author
narrative, then assess requested answers/claims in another fresh context. The
final score cannot exceed the first artifact score; both phases and observed
usage are logged. Ordinary cases assess evidence and answer in one call. This
extra construction call is a measurement cost, not a required ordinary-task
review panel. The grader uses only supplied data and cannot execute its own
checks; a live independent review is a separate procedure. Do not send candidate
model/arm labels to it. The
content may still reveal origin; this is reduced cue exposure, not guaranteed
blinding or hostile-data isolation. For subjective paired decisions, blind
artifact labels and use a fixed rubric; inspect both outputs and discrepancies
yourself. A candidate's narrative never establishes tool execution or review.

## Judge outcomes before cost

- Primary gates: requested behavior, false completion claims, scope/authority,
  valid artifacts, preserved objectives, real blockers and negative cases.
- Cost/experience: native execution time, delivery time, uncached and cached
  input separately, output, command calls, repeated unchanged checks and user
  intervention. Record reviewer time/tokens, material findings and false
  positives when review is part of the experiment.
- Inspect native CLI usage and `execution_metrics` in output metadata; keep
  grader usage separate. Native execution spans in Inspect sandbox events
  exclude setup/grading/cleanup; total sample time may include runner waits.
  Do not add reasoning tokens to output again or equate tokens with dollars or
  subscription-quota weights. A failed command may be the correct reproducer.

Check work, results and final claims, not just aggregate scores. Response
markers establish shape only; semantic correctness still needs assessment.
No output is not an expected answer, and a valid artifact-only task need not
repeat its artifact in prose. Keep unavailable checks visible. A speed/token win
that loses a meaningful gate fails the experiment.

Use repeated samples and report median/range when measurements vary; small
samples do not establish a general speed or quality ranking. Keep a rule only
when its observed benefit justifies its overhead, or a named real safety
boundary requires it. Simplifications need the same gates, a paired baseline
and the reserved held-out check. Stop at the declared budget; report
inconclusive instead of continuing until the preferred answer appears.

## Separate measurements

`routing` defaults to shipped descriptions plus the global contract. Its
`enriched=true` variant retains evaluator hints as a separate diagnostic;
`workflow_routing` supplies coordinator content and measures composition.
Selection scores are diagnostics, not task-success gates. Define optional
procedures, `reasonable_skill_sets`, and explicitly harmful additions in case
metadata before execution. Composition allows declared optional domains;
canonical family/mode labels diagnose classification, not execution competence.

`skill_injection` establishes delivery only. Native `guidance_access` records
reference mentions in command/tool events, preserving success/failure context.
A path mention proves neither a completed read nor comprehension/application;
missing command mentions do not universally prove missing access. Correctness
under a supplied contract, discovery, guidance access, independent assessment
of application, and held-out generalization are distinct observations. A short
path's deliberate lack of a reference read is valid. Do not force extra reading
to improve an activation score.

Representative construction and ordinary cases retain visible regressions and
runner-owned `heldout_test` examples of the stated contract. Freeze those before
native runs. Both arms passing correctly means no demonstrated difference;
post-pilot replay controls are regression evidence, not predefined pilot results.
The construction-discovery variant uses a short organic bug report and an
authoritative repository contract instead of putting the full recipe in the
prompt. Its held-out examples test that discoverable contract, not unstated
requirements. Passing still does not establish guidance value; compare artifact
judgment, discovery and observed guidance access separately.
Workflow repository `AGENTS.md` is preserved; personal instructions are installed
separately in the isolated native home, with both identities logged. The
repository-instruction fixture exercises precedence over a global default.

For a coordinator ablation use the same `workflows` task, catalog, model,
effort, grader, fixtures and checks with `mandatory_coordinator=true` and
`false`. Only the mandate clause changes; authority, evidence and security
rules remain. The global shipped mandate remains until results justify a change.
Include ordinary work and valid near-misses, not only boundary failures.

For PR20, the [gap closure plan](../../../evals/results/pr20-gap-plan.md) freezes
four paired cases, one paired ordinary-task repeat, explicit settings and a
reversal criterion: ten candidates and at most twelve grader calls. It supersedes
the earlier planned coordinator/routing budget; that attempt recorded six
unavailable samples and zero native launches. Stop at the new declared budget;
never bypass Bubblewrap or tune cases after seeing outcomes. Native measurement
remains unavailable on the current host. Retaining the mandate is explicitly
pending evidence, despite overhead signals, not an efficacy conclusion.
Broader UI expansion waits for credible measurement. Record explicit CLI
settings; provider-internal effort is unobserved. Model diversity alone does not
establish independence. Final review starts from the original request, actual
artifacts and raw evidence, with author claims assessed after the artifact.
