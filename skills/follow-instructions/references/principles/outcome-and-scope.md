# Outcome and scope

This local reference combines pstack's Outcome-Oriented Execution, Laziness
Protocol, and Subtract Before You Add. It is a decision aid, not a mandate to
perform a rewrite.

## Trigger

Use when the request is broad, a new dependency or service is being proposed,
or an implementation is accumulating compatibility layers and adjacent work.

## Decision rule

Define the observable end state and literal non-goals before choosing the
shape. Inspect existing capabilities and delete unnecessary work before adding
moving parts. For a planned migration or rewrite, optimize for the intended
verified target rather than preserving temporary states that have no owner.

## Procedure

1. State what a user, caller, operator, or maintainer should observe when done.
2. Write the non-goals that prevent a neighboring program from entering scope.
3. Identify the existing owner, interface, and project command that can already
   reach the outcome.
4. Remove dead paths, redundant adapters, and speculative options before
   introducing a new layer.
5. If a transition is necessary, name the target state, the temporary breakage
   that is acceptable, and the check that ends the transition.
6. Stop when the requested observable result is verified. Do not add a second
   system merely because it might be useful later.

## Principal-engineer lens

The high-level contribution is judgment about scope. A principal engineer
turns an ambiguous request into a sequence of coherent deliverables while
preserving option value. The useful artifact is the decision and its boundary,
not the size of the proposal.

## Evidence

The final diff should show that the owner and interface stayed narrow. The
completion report should name the observable result, non-goals, and the check
that proves the target state. A build alone does not prove the end state.

## Example

For a missing pagination row, keep the existing domain query and cursor
contract. Add the regression, correct the cursor owner, and traverse the real
path. Do not add a second persistence layer or generic pagination framework.

## Limit

Do not call all dependencies unnecessary. A real boundary, durability need, or
external contract can justify additional structure. This principle rejects
speculation, not necessary engineering.
