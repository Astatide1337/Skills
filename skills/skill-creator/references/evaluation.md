# Evaluate marginal value without creating another framework

Use the repository's existing Inspect tasks in `evals/skills.py`. Structure
validation proves catalog mechanics, not engineering effectiveness. Runner unit
tests prove their tested contracts, not successful model or browser execution.

## Design the comparison

Freeze a baseline and candidate catalog, identical project inputs, acceptance
checks, global instructions, available tools, and model/effort settings. Select
the model explicitly from the live supported catalog rather than relying on an
evaluator default or prescribing a particular provider/model forever. Preserve
unrelated dirty work in isolated disposable workspaces.

Start with two to four representative matched task pairs, alternating order:
a clear bug, a complete feature, simplification, ambiguous diagnosis, known-defect
and clean review, or version-sensitive framework work. Reserve untouched cases
before tuning. Use organic requests without telling candidates the rubric,
expected skill routes, comparison arm, or hidden acceptance. Keep every attempted
outcome, including failures and unavailable capabilities.

Compare current guidance with simplified guidance before adding tools. Trial
one addition against an observed gap, then promising complementary pairs and
leave-one-out removal where useful. Set time/spend limits before execution;
include nested candidate sessions, interrupted attempts, and any grader calls.
Do not expand a pilot until its results justify the cost. No paid grader or
live model use is required for structural implementation checks.

## Validate the runner before live use

Inspect the current implementation and CLI syntax; do not reuse stale command
flags as proof of compatibility. Model-free discovery includes:

```bash
./scripts/validate-skills.sh
python3 -m unittest discover -s evals/tests
uv run inspect list tasks evals/skills.py
python3 scripts/namespace-doctor.py
```

These are commands to run in a prepared environment, not claimed results.
Confirm binary resolution, authenticated status, native startup metadata,
permission profiles, and `bwrap_preflight` before comparisons. Follow the
runner's existing isolation contract: do not grant hidden acceptance, other-arm
catalogs, credentials, or unrelated paths to candidates. A receipt records
requested configuration; it does not establish execution or containment.
Unsupported required capabilities remain unavailable. Do not bypass isolation,
replace an integration with a mock, or label missing execution passed.

Use explicit task arms, frozen roots/globals, supported model/effort, case IDs,
and budgets. For model-free scoring of workflow runs, explicitly set
`include_behavior_grader=False`. Check exact parameter names with task discovery
before launch. The runner's default model is not permission to spend quota or
select a different daily model. Keep both arms identical except the treatment;
changing model/effort is a separate experiment.

Legacy approved-plan fixtures measure that explicit staged contract only; they
do not define an approval requirement for ordinary engineering. Keep historical
results identifiable as historical rather than prescribing their model, budget,
mandate, or unavailable host capabilities for every future experiment.

## Judge quality before cost

Required behavior, truthful claims, preserved unrelated changes, and authority
boundaries are gates. No introduced security/data-loss defect, unauthorized
scope expansion, merge, or deployment can be traded for speed. Inspect actual
artifacts and raw tool evidence before the author's narrative. Independent
review needs an actual returned review and applicable authorization; a grader
or differently named model does not establish it.

Measure useful valid findings, missed defects, false positives, acceptance,
failed calls, interruptions, elapsed time, tokens/cost when exposed, setup, and
maintenance. Unknown telemetry stays unknown; do not equate tokens with dollars
or double-count reasoning usage. Separate runner setup, candidate, review, and
grader costs where possible. Small samples support pilot decisions, not a
universal ranking. Both arms passing means no demonstrated quality difference.

Use unchanged held-outs once for the retained candidate. If they fail, restore
the last independently validated state and report the invalidated result; do
not tune on them and call the next result held-out. Stop at the declared budget
and report inconclusive when necessary. Promote only demonstrated improvements
or named real boundaries; remove unused or redundant machinery. Evaluation
never silently grants installation, publication, or global instruction edits.
