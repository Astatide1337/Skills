# Evaluate behavior and overhead

Use this procedure to design or run a skill evaluation. Before execution,
freeze the baseline and candidate catalogs and global instructions, project
files, requests, expected behavior, permissions, tools, model settings,
acceptance checks and finite candidate/grader budget. Use the same authorized
model and settings in both arms, after confirming runtime support.
Do not silently change the model or effort after a failed launch.

Derive cases from observed failures. Include ordinary tasks, different valid
solutions and nearby requests where the guidance should not apply. Reserve
held-out cases before changing the instructions; repeated runs of one case
are not independent tasks. Read [measured improvement](measured-improvement.md)
for baseline selection, testing related unseen tasks and adoption decisions.

Obtain independent review of the final candidate. Retain every attempt,
including failures and unavailable capabilities. A passing evaluation does
not authorize adoption; that needs a separate human-authorized decision.

## Calibrate before comparison

Apply [instrument validity](../../verify-work/SKILL.md#validate-the-measuring-instrument)
before treating a score as evidence of success. Test known-valid alternatives
and defects against the user's requirements. Assess changes to the evaluator
separately from changes to candidate guidance. Keep independent acceptance
checks fixed.

## Use existing Inspect tasks

The tasks in `evals/skills.py` run the locally authenticated Codex CLI in its
workspace sandbox. Personal configuration and unrelated installed skills are
excluded. Inspect owns execution, concurrency, logs, scorers and viewing.
Catalog behavior injects a selected skill verbatim; its no-skill baseline gets
neither guidance nor catalog. Workflows compare explicit catalog roots and
global instructions; a no-catalog diagnostic must be named as such. Test
installation and automatic selection separately from whether the instructions
improve results.

### Native executable and permissions

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

### Prepare the isolated catalog

Native startup replaces `.system` with CLI-owned bundled skills; do not put
selected catalog aliases there. Keep selected locators at the ordinary
`home/skills/<name>/SKILL.md` paths. Before each model session, a bounded
30-second model-free `debug prompt-input` command initializes the fresh owned
home. Enumerate only its concrete `.system/*/SKILL.md` files and disable every
one through the supported `skills.config` per-file `-c` selectors, including
future bundle names. Package-directory selectors do not filter the catalog.
Reject failed metadata initialization or linked/external paths before model
execution. This preparation writes no user config and reads no credential file
through the adapter. The normal CLI owns authentication handling.
The metadata child starts in its own process group. Cancellation or timeout
kills that owned group, drains inherited pipes even if its leader already
exited, and awaits the child before the home context closes;
preparation cannot recreate its removed home after an evaluation stops.

Both command profiles also deny the exact `home/skills/.system` directory.
The selected candidate keeps its canonical and ordinary logical catalog;
isolated grading receives no selected or bundled skill metadata. Record
`skills_eval.native_skill_startup` separately from the requested permissions:
its metadata digest and disabled selectors describe preparation, not successful
native command execution. Verify the filtered model-visible catalog and actual
command boundaries on the tested native ELF before efficacy comparison.

Frozen instruction bytes live in an ephemeral `~/.cache/work-guidance-*/skills`
snapshot; isolated Codex homes use `~/.cache/work-session-*`. Both use the
existing user-owned canonical cache directory and are removed when their
contexts close. Refuse a cache that resolves under `/tmp`, the configured
`TMPDIR`, or the default temporary directory before native launch. A catalog
snapshot must stay outside the denied temporary roots; do not restore access by
weakening the temporary-root policy. Grant only the selected snapshot and
logical skills directory, never the cache parent or surrounding authentication home.
Isolated grading workspaces also use `~/.cache/review-workspace-*` and retain
read-only workspace access with no catalog.
Ordinary candidate Inspect workspaces keep their existing location and
workspace-write binding.

Each returned native JSONL stream includes a runner-owned
`skills_eval.native_permissions` receipt with the requested profile and binary
SHA-256. Launch failures retain that configuration too. This records configuration, not successful execution. Before using the model,
test the profile on the actual host with harmless files and operations created
for the probe. Reads of the selected canonical/logical skills and workspace
must pass. Reads of hidden acceptance, the other arm and dummy authentication
files must fail through direct, symlink and proc-root paths. Excluded writes
and AF_INET socket creation must fail. Check workspace writes in the implementation
profile and their rejection in the grader profile. Run the actual fixture Python
command and retain its interpreter identity; a missing runtime is unavailable,
not permission to broaden filesystem access. A passing Bubblewrap prerequisite
alone does not establish these boundaries.

Check the selected native executable's help and run harmless probes through
the same profile and launch path the evaluator uses. Argument acceptance,
reported configuration and metadata preparation do not prove that generated
commands execute within the intended boundary. Local command checks do not
establish containment of hosted search, connected apps, MCP services or browser
traffic; required unsupported capabilities remain unavailable.

Native `fake-tracker-publication` is explicitly unavailable before launch: its
runner-owned Unix socket lives outside the workspace in an excluded temporary
root, and no scoped socket capability has been proved under `skills-eval`.
Do not grant a temporary root to restore that fixture. Deterministic FakeTracker
tests and `workflow_fixture_pilot` still exercise the local receipt contract;
their success does not establish native publication availability.

### Preflight and run

First run the deterministic checks and discover available tasks:

```bash
uv run --frozen python -m unittest evals.tests.test_workflows evals.tests.test_skills_lifecycle -v
uv run --frozen inspect list tasks evals/skills.py
python scripts/namespace-doctor.py
```

Check the actual CLI's supported model/effort and authenticated state before
authorized model use; `codex login status` is a read-only status check, not
permission to initiate login or change credentials. If the namespace is unsupported, record the run as unavailable. Do not weaken
isolation, substitute mocks for integration or report a pass. Live model use requires user authorization.

If the tool sandbox denies the namespace, inspect that failure and the ordinary
host's supported execution path. A permitted host retry must use the same
Bubblewrap gate and containment contract; it is not a bypass. Do not change
host namespace/security policy or remove the preflight. Keep the attempt and
remaining capability gap if the supported path also fails.

For an optional diagnostic, these commands compare a selected skill with no
skill. Set `SKILLS_EVAL_MODEL`, `SKILLS_EVAL_EFFORT`,
`SKILLS_EVAL_GRADER_MODEL` and `SKILLS_EVAL_GRADER_EFFORT` to the exact supported
selections established during preflight. Use the paired workflow commands below
to compare catalog versions:

```bash
uv run --frozen inspect eval evals/skills.py@catalog \
  -T native_model="${SKILLS_EVAL_MODEL:?Select a supported candidate model}" \
  -T native_effort="${SKILLS_EVAL_EFFORT:?Select supported candidate effort}" \
  -T grader_model="${SKILLS_EVAL_GRADER_MODEL:?Select a supported grader model}" \
  -T grader_effort="${SKILLS_EVAL_GRADER_EFFORT:?Select supported grader effort}" \
  --limit 2 --epochs 2 --max-samples 2 --time-limit 480
uv run --frozen inspect eval evals/skills.py@catalog -T with_skills=false \
  -T native_model="${SKILLS_EVAL_MODEL:?Select a supported candidate model}" \
  -T native_effort="${SKILLS_EVAL_EFFORT:?Select supported candidate effort}" \
  -T grader_model="${SKILLS_EVAL_GRADER_MODEL:?Select a supported grader model}" \
  -T grader_effort="${SKILLS_EVAL_GRADER_EFFORT:?Select supported grader effort}" \
  --limit 2 --epochs 2 --max-samples 2 --time-limit 480
```

Select representative sample IDs instead of the first two when appropriate.
`native_effort` controls candidates and routing. `grader_effort` and optional
`grader_model` configure assessment separately. Select values accepted by both
the evaluator and the resolved model rather than relying on an example or a
default. Record a rejected setting as failed or unavailable rather than silently
changing it. Keep both arms identical and the grader fixed while measuring an
instruction change. Measure a different
effort as a separate experiment. Parent Inspect model settings and token/cost
limits do not account for the nested CLI; use explicit sample time budgets and
inspect native usage. Do not describe a time limit as a quota cap.

## Observe the approved-plan lifecycle

Use the coordinator's [approved-plan contract](../../follow-instructions/references/approved-plans.md)
as the behavior being measured; the evaluator supplies observations, not a
second approval state model.

The `workflows` task includes realistic requests for initial plans, approved
continuation, new material findings, simplification within scope, safe recovery,
stalled-work handoff, tiny changes and stale approvals. Hidden
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

This records state at the two stage boundaries. It cannot detect writes
restored between snapshots or establish actual conversation resumption or
context compaction. HTML structure
alone does not establish a researched or visually correct plan; those claims
still need independent artifact assessment and actual browser evidence.
Keep these limits attached to results. Unit-test mocks exercise the adapter
contract only and are never native behavior outcomes.

The support gate blocks native launch for unobserved required capabilities.
General third-turn reapproval, actual independent peer review, remote CI, and
merge-attempt observation are not supplied by this local lifecycle adapter.
A fake tracker, fixture regression, grader, or candidate narrative cannot satisfy
them. The no-merge
delivery case deliberately retains these unavailable gates. Initial plan and
local continuation success cannot establish a PR ready for human merge.

For a bounded paired local lifecycle check, choose the same case IDs in both
arms and explicitly supply frozen `candidate_skills_root`,
`candidate_global_instructions`, `baseline_skills_root` and
`baseline_global_instructions`. For example, after those paths and the exact
CLI model are verified, use the preflight model/effort selections:

```bash
uv run --frozen inspect eval evals/skills.py@workflows -T arm=candidate \
  -T candidate_skills_root=/path/to/frozen-candidate/skills \
  -T candidate_global_instructions=/path/to/frozen-candidate/global-instructions/AGENTS.md \
  -T native_model="${SKILLS_EVAL_MODEL:?Select a supported candidate model}" \
  -T native_effort="${SKILLS_EVAL_EFFORT:?Select supported candidate effort}" \
  -T include_behavior_grader=false \
  -T 'case_ids=["workflow-native-plan-approved-continuation"]' \
  --epochs 1 --max-samples 1 --time-limit 480
uv run --frozen inspect eval evals/skills.py@workflows -T arm=baseline \
  -T baseline_skills_root=/path/to/frozen-baseline/skills \
  -T baseline_global_instructions=/path/to/frozen-baseline/global-instructions/AGENTS.md \
  -T native_model="${SKILLS_EVAL_MODEL:?Select a supported candidate model}" \
  -T native_effort="${SKILLS_EVAL_EFFORT:?Select supported candidate effort}" \
  -T include_behavior_grader=false \
  -T 'case_ids=["workflow-native-plan-approved-continuation"]' \
  --epochs 1 --max-samples 1 --time-limit 480
```

These two samples can launch four candidate sessions total. They omit model
grading intentionally and cannot establish semantic plan quality or efficacy.
Declare the independent assessment and any wider case/held-out budget before
starting it; count each approval phase, interrupted attempt and grader call.

## Withhold evaluation cues

Give candidates realistic requests and project files. Withhold the rubric,
expected routes, comparison arm and reference answer. Do not ask them to
recite skills or principles. Use neutral temporary paths and task guidance. Retain the
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
checks; a live independent review is a separate procedure. Do not send candidate model or arm labels to the grader. The content may still
reveal its origin, so this reduces cues without guaranteeing blinding or
isolating hostile data. For subjective paired decisions, blind
artifact labels and use a fixed rubric; inspect both outputs and discrepancies
yourself. A candidate's narrative never establishes tool execution or review.

## Judge outcomes before cost

- Check the requested behavior, artifact validity, scope and permissions,
  retained objectives, legitimate blockers and negative cases. Identify false
  completion claims.
- Measure native execution and delivery time, uncached and cached input
  separately, output, command calls, repeated unchanged checks and user
  interventions. Record reviewer time/tokens, material findings and false
  positives when review is part of the experiment.
- Inspect native CLI usage and `execution_metrics` in output metadata; keep
  grader usage separate. Native execution spans in Inspect sandbox events
  exclude setup/grading/cleanup; total sample time may include runner waits.
  Do not add reasoning tokens to output again or equate tokens with dollars or
  subscription-quota weights. A failed command may be the correct reproducer.

Check work, results and final claims, not just aggregate scores. Response
markers establish shape only; semantic correctness still needs assessment.
No output is not an expected answer, and a valid artifact-only task need not
repeat its artifact in prose. Keep unavailable checks visible. Lower time or token use does not compensate for a failed required check.

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
Selection scores diagnose routing; they do not establish task success. Define optional
procedures, `reasonable_skill_sets`, and explicitly harmful additions in case
metadata before execution. Composition allows declared optional domains. Family and mode labels show
whether the request was classified correctly, not whether the task was done
competently.

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

For a coordinator ablation, use the explicit baseline/candidate catalog and
global-instruction paths above. Keep the catalog, model, effort, grader,
fixtures and checks identical; change only the identified mandate clause in
the frozen candidate instructions. The legacy `mandatory_coordinator=false`
helper accepts retired policy wording, not the current shipped instructions.
Keep the shipped mandate until results justify a change. Include ordinary work
and valid near-misses, not only boundary failures.

Record the explicit CLI settings; the provider's internal effort is unobserved.
Using different models alone does not establish independence. Final review starts from the original request, actual
artifacts and raw evidence, with author claims assessed after the artifact.
