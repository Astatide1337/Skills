# Plans, authority and changed scope

Use for substantial implementation even when the design is settled, substantial
design decisions, or an explicit user or project approval requirement. The user's instructions determine
permission; a plan records that permission and does not expand it. Read-only
explanations, research and reviews stay read-only. Clear small changes use the
short path.

## Establish the decision

Build the recommendation before asking the user to approve it. Inspect the
responsible code, callers, tests, deployment configuration and a nearby accepted
implementation of the same kind. Reuse its ownership, naming and operational
path unless a concrete constraint makes that unsuitable. Check whether an
existing capability or smaller change already meets the request.

Keep the plan in the existing task record. It should answer:

- What observable outcome is required, and what is outside scope?
- Which existing owners and conventions will carry the change?
- What is the smallest complete implementation, and why does it fit?
- Which compatibility, failure or recovery concern could invalidate it?
- How will the actual behavior be verified, including useful before evidence?

Every substantial implementation plan must include an **Orchestration** section
in the existing task record. State:

- what the frontier owner will decide and integrate;
- which bounded tasks go to smaller workers, with model, reasoning level and
  required tools chosen through [agent selection](agent-selection.md);
- dependencies, file or environment ownership, and which tasks can overlap;
- the evidence each worker returns and how the parent checks the integrated result;
- who performs independent code review, using its separate model-selection rule.

Delegate as much bounded work as useful without duplicating exploration or
splitting unsettled interfaces. Same-provider workers are valid. If delegation
is unavailable or adds no useful work, give the concrete reason in this section
and proceed locally; do not create empty worker roles to satisfy the format.
Update assignments when runtime availability changes. This section does not
create another approval gate or require a committed plan file.

Resolve material factual unknowns with inspection or a bounded authorized
experiment before presenting a plan as executable. Compare alternatives only
when a real choice remains. Prefer fewer moving parts, dependencies and ongoing
operational obligations at equal correctness; a shorter patch that scatters
ownership or hides failure is not simpler. Trace a normal use and a plausible
failure through the proposed design. Consider the next likely maintenance change
from current callers and history, not hypothetical future platforms.

For a substantial or consequential design, obtain an independent challenge
before dependent implementation when delegation is available. Give the reviewer
the original request, relevant code, proposed change and acceptance; ask for
concrete reasons a maintainer would reject it, not endorsement. Resolve material
findings and update the affected decision before presenting it for approval.
A clean review does not guarantee correctness or replace execution evidence.
If review is unavailable, state that limit rather than claiming it occurred.

Match precautions to observed state. Verify the actual target, dependencies and
data before treating an environment as disposable. Re-creatable isolated test
state usually needs a reset path, not a new backup system. Shared consumers,
unique data or production traffic require recovery appropriate to that exposure,
even when the environment is named “test.” Reuse established deployment and
recovery procedures; do not invent infrastructure for a routine change.

Present the decision, reason, essential steps and meaningful remaining tradeoff
concisely. Do not make the user detect missing research in a long checklist.
Produce a separate plan artifact only when requested or needed for a decision;
use the requested format. Approval authorizes the agreed work; it does not prove
the design is sound or discharge verification.

An investigation does not authorize permanent tooling; first establish the
recurring need and missing native capability. For uncertain UI direction,
exercise one representative interaction before expanding screens; use [UI
prototyping](../../web-interface/references/ui-prototyping.md) when a prototype
is relevant.

Keep the requested deliverable and format through research and delegation.
Working notes do not replace an explicitly requested HTML plan or other output.
Check the final file's format and inspect its rendering when required.

## Apply the actual approval gate

When the user or project requires a design approval, prepare the concrete
reviewable result in the requested format, identify its version and ask only for
the unresolved decision. Preserve explicit HTML/prototype approval requests.
Keep presentation separate from authorization: an HTML plan does not itself
require a new approval round. When implementation and delivery are already
authorized, proceed within that scope and honor any task-specific planning waiver.
Record the original request or confirmation and any later superseding decision.

When evidence changes the design, update the affected decision. Continue in-scope
repairs and safe independent work. Ask before dependent work only when the change
requires permission not yet given or an essential product decision, changes an explicitly
approved contract, or crosses a user/project approval gate. A reviewer suggestion
is evidence to assess, not permission or a new requirement.

Resolve routine engineering choices from the request, source, conventions and
prior decisions. Ask only when an essential product choice remains unresolved
or the action needs authority not already given. State the recommended option
and practical consequence; continue work independent of that answer. A broad
prompt calls for grounded judgment, not invented requirements or repeated approval.

## Continue and retain acceptance

Authorized PR/MR delivery follows the single
[delivery completion contract](../../pull-requests/SKILL.md#complete-authorized-delivery).
Local-only work ends at its requested verified artifact. Neither path authorizes
merge, deployment or adjacent cleanup. Keep original acceptance, failed approaches,
current result and unfinished checks in the existing task record; use
[durable checkpoints](durable-checkpoints.md) before a real interruption.

A plan-only request ends with the researched decision and remaining unknowns.
An implementation request continues through its authorized completion, rather
than ending at the plan, draft, first passing check or first reviewer finding.
