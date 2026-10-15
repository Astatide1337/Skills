# Plans, authority and changed scope

Use when a substantial implementation needs a design decision, or the user or
project explicitly requires approval. Direct instructions determine authority;
a plan records it and never grants additional effects. Read-only explanations,
research and reviews stay read-only. Clear small changes use the short path.

## Establish the decision

Inspect the actual owner, callers, existing automation, constraints and checks.
State the desired outcome, smallest correction, affected interfaces, permitted
effects and acceptance in the existing task record. Use a concise plan unless
the user requests another format. A bounded investigation does not authorize
permanent tooling; first establish the recurring need and missing native capability.
For uncertain UI direction, exercise one representative interaction before
expanding screens; use [UI prototyping](../../web-interface/references/ui-prototyping.md)
when a prototype is relevant.

## Apply the actual approval gate

When the user or project requires a design approval, prepare the concrete
reviewable result in the requested format, identify its version and ask only for
the unresolved decision. Preserve explicit HTML/prototype approval requests.
When implementation and delivery are already authorized, proceed within that
scope; an HTML document or another approval round is not a default prerequisite.
Record the original request or confirmation and any later superseding decision.

When evidence changes the design, update the affected decision. Continue in-scope
repairs and safe independent work. Ask before dependent work only when the change
needs unavailable authority or an essential product decision, changes an explicitly
approved contract, or crosses a user/project approval gate. A reviewer suggestion
is evidence to assess, not permission or a new requirement.

## Continue and retain acceptance

Authorized PR/MR delivery follows the single
[delivery completion contract](../../pull-requests/SKILL.md#complete-authorized-delivery).
Local-only work ends at its requested verified artifact. Neither path authorizes
merge, deployment or adjacent cleanup. Keep original acceptance, failed approaches,
current artifact and unfinished gates in the existing task record; use
[durable checkpoints](durable-checkpoints.md) before a real interruption.

A plan-only request ends with the researched decision and remaining unknowns.
An implementation request continues through its authorized completion, rather
than ending at the plan, draft, first passing check or first reviewer finding.
