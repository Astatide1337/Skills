# Evaluate behavior and overhead

Use when running or designing skill evaluations. Freeze the representative
request, expected observable behavior, authority, tools, candidate/baseline
instructions, model and effort, finite run budget and acceptance gates before
execution. Derive cases from observed failures; include ordinary tasks and
valid near-misses, not only adversarial traps. Reserve held-out cases before
choosing instruction changes. Repetitions are not independent tasks.

For the approved engineering workflow, implement the complete candidate,
portable lint repairs and deterministic lifecycle tests before comparison.
Obtain independent review of that final candidate. Freeze the baseline and
candidate catalogs/globals, project files, organic tasks, settings, held-out
checks and a finite candidate/grader budget together. The current comparison
uses **GPT-6 Luna candidates in both arms with identical explicit settings**;
do not silently substitute another model or effort after a failed launch.
Retain every attempted outcome, including unavailable capabilities and failed
samples. Self-learning and automatic rule promotion remain paused; any later
promotion is a separate human-authorized decision.

## Use existing Inspect tasks

The tasks in `evals/skills.py` run the locally authenticated Codex CLI in its
workspace sandbox. Personal configuration and unrelated installed skills are
excluded. Inspect owns execution, concurrency, logs, scorers and viewing.
Catalog behavior injects a selected skill verbatim; its no-skill baseline gets
neither guidance nor catalog. Workflows compare explicit catalog roots and
global instructions; a no-catalog diagnostic must be named as such. Test
installation/automatic routing separately from instruction efficacy.

Native launches require a direct executable on PATH. If `codex` is an npm or
script wrapper, supply the absolute trusted native ELF through
`SKILLS_CODEX_NATIVE_BINARY`; the adapter refuses wrappers rather than guessing
their installation layout. Verify and freeze that binary's version and hash
before comparison, and use the same executable in both arms.

`run_codex` selects the ephemeral `skills-eval` permission profile through
`default_permissions` and `-c` overrides. It retains `--ignore-user-config`,
`--ignore-rules` and `--strict-config`, and removes the legacy `--sandbox`
selector. Workspace-write extends `:workspace`; grading extends `:read-only`.
Both deny root reads, allow `:minimal` and the exact native executable, deny
temporary roots and direct network access, and grant only the current workspace
with the requested read/write access. Installed-catalog runs additionally grant
the selected canonical catalog and its logical home/skills directory. Neither
the surrounding Codex home, authentication file, other arm nor evaluator source
receives a read grant. Grading receives a separate empty workspace.

Each returned native JSONL stream includes a runner-owned
`skills_eval.native_permissions` receipt with the requested profile and binary
SHA-256. Launch failures retain that configuration too. This is configuration
provenance, not execution proof. Before model use, test the generated profile on
the actual host using owned canaries: selected canonical/logical skills and
workspace reads must pass; hidden acceptance, other-arm and dummy-auth reads
must fail through direct, symlink and proc-root paths; excluded writes and
AF_INET socket creation must fail. Check workspace writes in the implementation
profile and their rejection in the grader profile. Run the actual fixture Python
command and retain its interpreter identity; a missing runtime is unavailable,
not permission to broaden filesystem access. A passing Bubblewrap prerequisite
alone does not establish these boundaries.

Codex 0.162.0 accepts the named profile in `command/exec` and reports it in idle
`thread/start` without a model turn. `codex exec --help` verifies argument support;
it does not prove a generated command ran. Model-free `debug prompt-input` can
show the requested restricted profile but rejects `--strict-config`. The native
CLI's sandbox command is `codex sandbox -P skills-eval -- COMMAND`. These local
command checks do not establish containment of hosted search, connected apps,
MCP services or browser traffic; required unsupported capabilities remain
unavailable.

Native `fake-tracker-publication` is explicitly unavailable before launch: its
runner-owned Unix socket lives outside the workspace in an excluded temporary
root, and no scoped socket capability has been proved under `skills-eval`.
Do not grant a temporary root to restore that fixture. Deterministic FakeTracker
tests and `workflow_fixture_pilot` still exercise the local receipt contract;
their success does not establish native publication availability.

First run the deterministic owner checks and task discovery:

```bash
uv run --frozen python -m unittest evals.tests.test_workflows evals.tests.test_skills_lifecycle -v
uv run --frozen inspect list tasks evals/skills.py
python scripts/namespace-doctor.py
```

Check the actual CLI's supported model/effort and authenticated state before
authorized model use; `codex login status` is a read-only status check, not
permission to initiate login or change credentials. An unsupported namespace fails
honestly; never weaken isolation, replace integration with mocks or label the
unavailable run passed. Live model use requires user authorization.

If the tool sandbox denies the namespace, inspect that failure and the ordinary
host's supported execution path. A permitted host retry must use the same
Bubblewrap gate and containment contract; it is not a bypass. Do not change
host namespace/security policy or remove the preflight. Keep the attempt and
remaining capability gap if the supported path also fails.

Example bounded paired catalog runs:

```bash
uv run --frozen inspect eval evals/skills.py@catalog -T native_model=gpt-6-luna -T native_effort=medium -T grader_effort=high --limit 2 --epochs 2 --max-samples 2 --time-limit 480
uv run --frozen inspect eval evals/skills.py@catalog -T with_skills=false -T native_model=gpt-6-luna -T native_effort=medium -T grader_effort=high --limit 2 --epochs 2 --max-samples 2 --time-limit 480
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

## Observe the approved-plan lifecycle

Use the coordinator's [approved-plan contract](../../follow-instructions/references/approved-plans.md)
as the behavior being measured; the evaluator supplies observations, not a
second approval state model.

The existing `workflows` task includes organic initial-plan, approved
continuation, material-discovery, in-contract simplification, safe-recovery,
stall-handoff, tiny-change and stale-approval fixtures. Hidden
`fixture_contract`, held-out checks, comparison labels and continuation metadata
stay in the runner, outside candidate input. The project files and initial
request stay identical across catalog arms; only their catalog/global guidance
differs.

`workflow-native-plan-approved-continuation` uses the existing native adapter
and two `run_codex` sessions. After session one exits, runner workspace evidence
must be complete and show only permitted plan-stage paths, with no Git control
or index changes. A bounded regular HTML plan must exist. Only then does the
runner supply the user confirmation bound to its observed SHA-256. Session two
gets the original objective plus that confirmation, the same frozen catalog,
and identical model/effort. The final scorer rejects a changed or missing
approved plan and runs the frozen original/held-out acceptance on the final
implementation. Both phases' emitted usage is retained and summed; a missing
field stays unknown.

This observes persisted stage boundaries, not writes later restored between
snapshots, actual conversation resumption or context compaction. HTML structure
alone does not establish a researched or visually correct plan; those claims
still need independent artifact assessment and actual browser evidence.
Keep these limits attached to results. Unit-test mocks exercise the adapter
contract only and are never native behavior outcomes.

The support gate blocks native launch for unobserved required capabilities.
General third-turn reapproval, actual independent peer review, remote CI, and
merge-attempt observation are currently unavailable. A fake tracker, fixture
regression, grader, or candidate narrative cannot satisfy them. The no-merge
delivery case deliberately retains these unavailable gates. Initial plan and
local continuation success cannot establish a PR ready for human merge.

For a bounded paired local lifecycle check, choose the same case IDs in both
arms and explicitly supply frozen `candidate_skills_root`,
`candidate_global_instructions`, `baseline_skills_root` and
`baseline_global_instructions`. For example, after those paths and the exact
CLI model are verified:

```bash
uv run --frozen inspect eval evals/skills.py@workflows -T arm=candidate -T candidate_skills_root=/path/to/frozen-candidate/skills -T candidate_global_instructions=/path/to/frozen-candidate/global-instructions/AGENTS.md -T native_model=gpt-6-luna -T native_effort=medium -T include_behavior_grader=false -T 'case_ids=["workflow-native-plan-approved-continuation"]' --epochs 1 --max-samples 1 --time-limit 480
uv run --frozen inspect eval evals/skills.py@workflows -T arm=baseline -T baseline_skills_root=/path/to/frozen-baseline/skills -T baseline_global_instructions=/path/to/frozen-baseline/global-instructions/AGENTS.md -T native_model=gpt-6-luna -T native_effort=medium -T include_behavior_grader=false -T 'case_ids=["workflow-native-plan-approved-continuation"]' --epochs 1 --max-samples 1 --time-limit 480
```

These two samples can launch four candidate sessions total. They omit model
grading intentionally and cannot establish semantic plan quality or efficacy.
Declare the independent assessment and any wider case/held-out budget before
starting it; count each approval phase, interrupted attempt and grader call.

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

Historically, the PR20 [gap closure plan](../../../evals/results/pr20-gap-plan.md) froze
four paired cases, one paired ordinary-task repeat, explicit settings and a
reversal criterion: ten candidates and at most twelve grader calls. It superseded
the earlier planned coordinator/routing budget; that attempt recorded six
unavailable samples and zero native launches. Stop at the new declared budget;
never bypass Bubblewrap or tune cases after seeing outcomes. Its unavailable
host result and restricted pilot scope are historical evidence, not a current
capability check or a restriction on the approved complete-workflow request.
Retaining the mandate remains pending efficacy evidence despite overhead
signals. Record explicit CLI
settings; provider-internal effort is unobserved. Model diversity alone does not
establish independence. Final review starts from the original request, actual
artifacts and raw evidence, with author claims assessed after the artifact.
