# PR20 gap closure plan and coordinator decision

Status: implementation and contract verification are separate from native
efficacy. PR20 is not ready for merge while the coordinator comparison remains
unavailable. This plan addresses the review of `98b22ba`; it does not reinterpret
historical runs as controlled evidence.

## Authorized scope and completion

Outcome: credible measurements of task outcomes, discovery and coordinator cost.
Route: implementation with evaluation, instruction review and the existing PR20
publication follow-on. Domains: skill-creator, writing-for-agents,
code-review-and-quality and verify-work. Effects: bounded repository edits,
tests, independent review, commit/push and PR update; no merge, credentials,
security configuration or application-repository changes.

1. Add one construction-discovery fixture. The short request describes the
   observed bug; a repository-owned contract and actual caller expose all
   requirements. Keep visible smoke checks and runner-owned negative examples.
   Replay correct alternative implementations and plausible incomplete fixes.
   Passing is correctness under a discoverable contract, not proof of guidance
   value or principal-engineer competence.
2. For construction evaluation only, assess artifacts in a fresh grader context
   before exposing the final author narrative. Preserve that assessment before
   a separate claim assessment; claims cannot raise the artifact score. Log both
   phases and costs. Ordinary cases retain one grader call. Clarify the same
   input order for risk-triggered independent review without adding a mandatory
   second reviewer or model-diversity rule.
3. Freeze the small coordinator comparison below before execution. Keep the
   existing mandate pending evidence, explicitly despite historical overhead
   signals and without a successful mandate-isolating comparison. Neither an
   unrun comparison nor unchanged instructions establishes value.
4. Run prerequisite diagnostics, targeted regressions and the complete
   applicable suite; obtain an independent GPT-6.1 Sol review of the original
   request, actual diff and raw evidence. Fix material findings, publish only
   the inspected changes to PR20, and verify exact-head CI. Report unavailable
   native execution and leave PR20 unmerged.

## Frozen bounded experiment

Use the existing Inspect `workflows` task, not a new runner. Freeze the commit,
catalog/global/fixture digests, CLI version, candidate `gpt-5.6-luna` at
`medium`, grader `gpt-5.6-luna` at `high`, concurrency 1, one epoch per batch
and a 480-second total sample limit including grading. Parent
`mockllm/model` is bookkeeping only: every candidate and grader uses the real
native CLI. Inspect token/cost limits do not cap nested CLI usage.

Compare the same catalog with `mandatory_coordinator=true` and `false`.
Only mandatory entry changes; authority, security, evidence rules, fixtures,
checks, model and effort are identical. The optional arm can select the
coordinator. Record whether it actually did; this is a policy comparison, not
an assumption of zero coordinator use.

Cases, in fixed order:

- `workflow-native-small-task`: ordinary mechanical correction.
- `workflow-native-artifact-only`: valid near-miss with optional prose.
- `workflow-native-repository-instructions`: repository precedence.
- `workflow-native-construction-discovery`: organic bug and discoverable contract.

Budget: eight initial candidate executions (four per arm), then one paired
repeat of the small task, reversing arm order: ten candidates total, at most
twelve grader calls (construction uses two phases), excluding the final human/
agent diff review. Failures/timeouts consume budget; no retries or case tuning
after observing results. Do not launch candidates if prerequisites fail; record
the diagnostic and stop. The earlier six unavailable samples remain a separate
attempt, with zero native launches. A no-catalog comparison would answer a
different question and is deferred rather than added to this budget.

On an authenticated namespace-capable host, first run:

```bash
uv run --frozen python scripts/namespace-doctor.py
codex login status
uv run --frozen inspect list tasks evals/skills.py
```

Run each case separately in the fixed order above, mandatory then optional.
Set `pr20_case` to the listed ID and `pr20_mandatory` to `true` then `false`:

```bash
uv run --frozen inspect eval evals/skills.py@workflows --model mockllm/model \
  -T arm=candidate -T mandatory_coordinator="$pr20_mandatory" \
  -T native_model=gpt-5.6-luna -T native_effort=medium \
  -T grader_model=gpt-5.6-luna -T grader_effort=high \
  --sample-id "$pr20_case" --epochs 1 --max-samples 1 --max-retries 0 \
  --time-limit 480 --log-dir "/tmp/pr20-coordinator-$pr20_mandatory"
```

For the final small-task repeat, optional goes first. Retain raw `.eval` logs
and inspect them with `inspect_ai.log.read_eval_log` in the existing uv
environment. Verify all ten IDs/arms and actual settings; do not infer launched
trials from requested counts. Do not transfer authentication to hosted CI.

## Predefined decision rule

Behavior gates come first: runner acceptance and workspace policy must pass;
required answers must exist, claims must match raw evidence, and independent
artifact assessment must find no material ownership, compatibility, failure
handling or authority defect. Do not gate on skill names, reference-read counts
or one preferred implementation. Unavailable evidence is inconclusive.

Report per-case native elapsed time (excluding grading), uncached/cached input,
output, commands and grader cost separately. Both arms passing is no
demonstrated quality difference. This small cohort cannot establish universal
efficacy; two repetitions are not independent tasks.

- Recommend narrowing/removing mandatory entry for the tested ordinary class
  if the optional arm preserves every gate, the mandate prevents no material
  failure in this cohort, and both small-task pairs show at least 20% more
  uncached input for the mandate without an optional-arm elapsed regression
  exceeding 20%. This is a bounded decision signal, not statistical proof.
- Retain only a demonstrated trigger if the mandate prevents a material failure
  confirmed from artifacts/raw evidence with an independently chosen diagnostic.
  A label/read difference or a higher grader score alone is insufficient.
- Mixed behavior, missing usage, inconsistent costs, or both arms voluntarily
  using the same path without a cost difference is inconclusive. Report it and
  stop; any larger experiment needs a new budget and frozen design.

Global entry remains unchanged in this increment. The result above would
justify a separately reviewed narrowing patch with the same gates replayed.
Historical 26.7k/10.1k input and 49.6s/24.0s ordinary-task observations motivate
the comparison but do not isolate mandatory entry. No successful comparison is
available on the current host: Bubblewrap cannot create the required namespace.
Tooling CI establishes tooling contracts, not agent benefit. Broad UI/design
benchmarks wait; authoritative convention discovery, product wording,
accessibility and actual user-flow verification remain objectives.
