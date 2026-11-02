# Plans, authority and changed scope

Use when a substantial implementation needs a design decision, or the user or
project explicitly requires approval. The user's instructions determine
permission; a plan records that permission and does not expand it. Read-only
explanations, research and reviews stay read-only. Clear small changes use the
short path.

## Establish the decision

Inspect the responsible code, callers, existing automation, constraints and
checks. Record the desired outcome, smallest correction, affected interfaces,
permitted actions and acceptance criteria in the existing task record. Use that
compact record for ordinary implementation. Produce a separate plan artifact
when requested or when it helps the user decide; choose HTML for useful visual
comparison or interaction. Otherwise use the requested prose format.

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
