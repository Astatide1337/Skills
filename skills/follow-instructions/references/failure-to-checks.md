# Confirmed failure to check map

This map abstracts confirmed, in-scope incidents from a private local audit. It excludes ambiguous intent changes, suspected omissions, excluded evaluation work, credentials, raw histories, and project-specific data. Use a row only when its trigger is present; the owning skill supplies the detailed procedure.

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
