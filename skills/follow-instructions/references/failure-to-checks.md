# Confirmed failure to check map

This map abstracts confirmed, in-scope incidents from a private local audit. It excludes ambiguous intent changes, suspected omissions, excluded evaluation work, credentials, raw histories, and project-specific data. Use a row only when its trigger is present; the owning skill supplies the detailed procedure.

## Provenance and limits

The original rows below informed this PR's implementation from private audit
summaries. Their underlying machine-specific records are not packaged here;
this repository cannot establish which incidents belong to K-Agent or
Lestatide. Preserve those as unestablished rather than guessing attribution.

The later March–August historical export supplied retrospective corroboration
and additional regression examples. It contains copied histories, including
external-agent conversations imported into another agent's session format;
source-file counts and session labels are not independent task or model counts.
It predates the current verification/routing revisions. A mapping or a passing
synthetic fixture does not certify that its original application incident is
fixed or that today's catalog reliably prevents it.

## Original implementation inputs

| Area | Decision | Observed failure | Required verification procedure | Owner |
| --- | --- | --- | --- | --- |
| Environment | Mark a dependency unavailable | A long task stopped on stale assumptions although the current checkout and connected tool worked. | Recheck the exact checkout, instance, and dependency with a current direct call before blocked status. | follow-instructions, self-reflect |
| Environment | Announce a preview or release | A served page linked to a route that returned 404; a separate release crashed after a green build. | Request the advertised URL and exercise the hydrated user path at the current revision. | verify-work |
| Verification | Accept a generated artifact | A failed render left an older artifact that was inspected as current. | Require exit status, fresh artifact identity, and inspection of that exact output. | verify-work |
| Verification | Claim a visual or media behavior | A control looked active while playback failed; a requested visual became a progress display; a narrow layout overlapped. | Drive the actual action and inspect the result at the requested browser or viewport, including motion or sound where claimed. | verify-work |
| Context | Resume a long task | A still-active objective vanished at handoff and safe release gates were left unfinished. | Retain objective, accepted decisions, unfinished gates, and next action; continue safe work. | follow-instructions, self-reflect |
| Context | Escalate for user input | Facts already in authoritative local material or a connected mailbox were treated as human blockers. | Check the named source and live question wording first; present all currently visible missing facts together. | follow-instructions |
| Context | Send an external message | Additional messages were sent outside an authorized count and time window. | Check recipient, purpose, count, and window before every send. | production-safety |
| Engineering Constraints | Recover a conflicted write | Loading the latest revision discarded a user's unsaved draft. | Keep draft and server revision separate; reject stale write without discarding input, then retry once after reconciliation. | architect, verify-work |
| Engineering Constraints | Add or replace a shared view | Two lanes showed one archived item; another view disagreed with the canonical state. | Derive all surfaces from one authoritative selector and test an archive/restore or prerequisite transition. | architect, code-review-and-quality |
| Engineering Constraints | Specify an auth or data rule | An unsupported token-header assumption denied the owner; templates were counted as records. | Parse external shape at the boundary, classify before counting, and run allowed plus rejecting fixtures. | security-and-hardening, verify-work |
| Loops | Retry a stateful create | An ambiguous result was retried into duplicate resources and cleanup used only a name. | Observe by stable identity before retry; refuse destructive cleanup without exact identity and authorization. | production-safety |
| Loops | Wake or continue a worker | Generic message updates caused repeated wakeups; a continuous loop waited for an hourly schedule. | Trigger on the requested transition, dedupe by state identity, and check the actual next-start interval. | architect, self-reflect |

A structural rule is justified when an observed recurrence or safety boundary can be enforced. State the approved pattern, forbidden alternative, enforcement point, and a violating fixture that fails. Keep app-specific types, schemas, lint/import rules, CI, and feature maps in the application; keep deterministic operations in a pinned per-app CLI.

## Later regression coverage

These cases extend the existing [workflow dataset](../../../evals/cases/workflows.json).
Each target and runner assertion is defined before candidate execution and kept
outside the candidate prompt. The case's `audit_provenance` distinguishes the
source class, unestablished machine identity, and limited implementation claim.

| Case | Source and cause | Observable prevention |
| --- | --- | --- |
| `workflow-native-stale-evidence` | Historical inspection: a prior result was promoted to current user-flow proof after changed inputs. | Inspect provenance, run the affected current check, and retain the failure rather than claim completion. |
| `workflow-native-required-answer` | Existing evaluator regression: an expected answer could substitute for missing candidate output; independent review was also confused with author review. | Require the requested answer separately from a correct artifact; keep independent review pending without a separate reviewer. |
| `workflow-native-interrupted-objective` | Original private audit summary: unfinished acceptance was lost through a handoff. | Complete every retained requirement and run the original regression. This is a simulated resume, not a context-compaction test. |
| `workflow-native-recoverable-debugging` | Original private audit summary: a stale capability assumption became a blocker. | Probe the current dependency-free check, reproduce the failure, fix its owner, and rerun that check. |
| `workflow-native-artifact-only` | Valid near-miss for the missing-answer guard. | Accept the required artifact without demanding redundant prose or unrelated runtime proof. |
| `workflow-native-genuine-blocker` | Valid near-miss for capability recovery. | Inspect the current verifier and report missing deployment evidence under local-only authority; do not manufacture a receipt. |
| `workflow-native-cancellation-effects` | User-reported audit scenario; underlying machine record uncorroborated here. | Exercise early, pending, post-commit, and normal cancellation boundaries. Late cancellation reports the completed save rather than pretending to undo it. |

Other historical findings, including invalid CI job references and failures in
startup/reset/report-combination paths, reinforce `systematic-debugging`'s
environment checks and `verify-work`'s claim boundaries. They have not received
application-level fixes or native integration coverage in this PR.

## Additional mechanisms and their limits

| Observed gap | Addition | Observable contract and remaining limit |
| --- | --- | --- |
| Original summaries: objective and unfinished gates lost at handoff. | [Durable checkpoints](durable-checkpoints.md) and `workflow-native-process-resume`. | Atomic revisioned records refuse stale updates or silent replacement of objectives, requirements and decisions. The runner interrupts an actual CLI process and a fresh session resumes from the record. This does not test every context-compaction mechanism. |
| Original summaries: green builds and old artifacts promoted to working user journeys; later exports: startup/reset failures. | [User-owned profiles](../../verify-work/references/portable-profiles.md). | Existing app-owned commands must satisfy independent exact expectations with unchanged declared source through cleanup. Failed startup attempts cleanup and later drives remain not-run. This does not install a browser harness or fix the audited applications. |
| Original summaries: discarded conflicted drafts, divergent shared views, duplicate retries; separately user-reported cancellation. | [State and lifecycle guidance](../../architect/references/state-and-lifecycle.md). | Design and verification identify state owner, commit boundary, preservation of drafts, stable retry identity, and pre/post-commit negative outcomes. These decisions still need implementation and runtime checks in the application. |
| Later retrospective exports: undefined CI dependency and executable schema replaced by prose. | `verify-work/scripts/boundary_checks.py`. | Exact JSON contracts and static CI job references reject controlled violating fixtures; valid optional dependencies remain accepted. Not a full CI platform validator or automatically installed application lint. |

The portable helpers are supplied identically to both arms of the native
resume comparison. Only the selected catalog instructions differ. The grader's
acceptance remains separate from candidate output. Subprocess/file controls
establish helper behavior; a small live trial does not establish broad agent
reliability or resolve attribution to K-Agent versus Lestatide.

The table lists procedures to perform when their triggers arise; its prose is
not an installed automated guard. Implemented checks are separate: the
[workflow contract tests](../../../evals/tests/test_workflows.py) exercise
runner-owned acceptance, and the
[candidate-output regression](../../../evals/tests/test_skills_lifecycle.py)
rejects a missing required answer even when the expected answer is available.
The [Catalog validation workflow](../../../.github/workflows/catalog-validation.yml)
runs catalog structure and case validation plus these model-free, local/mocked
unit contracts. Its separate Workspace evidence unit tests job installs
Bubblewrap from Ubuntu's package repository and attempts the full model-free
unit suite, including disposable local workspace observations. This is not
live model or adversarial workspace-containment evaluation. Report the actual
hosted result, including a blocked namespace preflight if it occurs, with its
revision; never count a blocked suite as a pass.

The workspace suite now checks its namespace prerequisite before creating test
baselines. An unsupported host fails once with an actionable reason instead of
continuing with unavailable baselines; isolation and integration assertions stay
enabled. Native trials snapshot and hash the loaded catalog's instructions,
references, and scripts. Git HEAD is context, not the identity of dirty bytes.
Response-marker checks report only observed shape, with semantic acceptance
left to the independent behavior grader. Model-free fixtures remain evaluator
contract checks, never evidence of agent efficacy.
An additional runner regression reproduces a passing supplemental check that
creates an out-of-scope file after evidence was cached. Workflow checks now run
before policy/behavior scoring and invalidate earlier evidence, so the final
observation includes those effects rather than accepting the stale snapshot.
