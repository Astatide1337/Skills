# Authority and claims

This local reference adapts pstack's Prove It Works, Never Block on the Human,
and Encode Lessons in Structure to the repository's explicit authority model.

## Trigger

Use before a completion claim, external write, publication, merge, deployment,
or a decision to continue after an ambiguous result.

## Decision rule

Separate what the user requested, what the available tool can do, and what the
evidence proves. Proceed with reversible in-scope work without unnecessary
permission pauses. Stop before irreversible or unauthorized effects. Distinguish
drafting, fixing, creating, publishing, merging, and deploying.

## Procedure

1. State the exact target, authorized effect, source of truth, and current
   revision or artifact.
2. Inspect the final artifact and the actual execution path at the layer named
   by the request.
3. If a write is ambiguous, inspect existing state before retrying. Preserve
   object identity and avoid duplicate effects.
4. Re-read the relevant boundary and rollback obligations before publication.
5. Narrow the claim to the evidence. Name unsupported integrations, missing
   telemetry, and blocked environments.
6. When a recurring authority or evidence error is deterministic, encode the
   check in the owning workflow rather than adding another reminder.

## Principal-engineer lens

Trust is a technical property. Principal-level stewardship means that other
people can rely on the claimed state, the scope of a change, and the boundary
between recommendation and action.

## Evidence

Use the actual diff, runtime output, written object, readback, or deployed
behavior appropriate to the claim. A green build proves a build. It does not
prove a browser journey, production health, comprehension, or superiority.

## Example

An issue marked draft is useful copy but not a published issue. A successful
create must be followed by a same-object readback when publication is the
requested result.

## Limit

Do not turn a small local explanation into a publication report. The amount of
authority and evidence work should match the consequence of the action.
