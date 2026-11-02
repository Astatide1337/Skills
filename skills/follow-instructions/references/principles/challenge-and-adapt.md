# Challenge and adapt

Adapted from pstack's Attack the Premise, Redesign From First Principles, and
Exhaust the Design Space.

## Trigger

Use when related fixes fail the same gate, a new requirement is being bolted
onto an existing design, or a novel UI/architecture choice has no useful
precedent.

## Decision rule

Write the shared premise and test it against current evidence before adding
another workaround. For a genuinely novel choice, compare two or three
structurally different options. When a requirement should have shaped the
system from the beginning, redesign the affected boundary coherently instead
of preserving accidental compatibility forever.

## Procedure

1. Record the repeated failure or new requirement and the premise behind the
   current approach.
2. Inspect the actors, state, callers and work assignments that could produce
   the failure. If uneven distribution may be the cause, count it with a small
   repeatable check.
3. Decide whether the answer is already constrained by an established pattern.
   If so, use it. If not, compare materially different designs or prototypes.
4. Propagate the chosen requirement through types, callers, docs, tests, and
   recovery behavior. Do not leave an old path active accidentally.
5. Re-run the discriminating check. Keep the rejected alternative and reason
   only when it helps a future decision.

## Evidence

Show the premise, the observation that challenged or supported it, and the
choice that changed. For a prototype, record the comparison and when its
assumptions need rechecking. For a clear bug, the original regression is
stronger evidence than an unnecessary comparison of designs.

## Example

If evaluator hardening repeatedly grows while a real workflow remains
unmeasured, pause expansion and test one supervised repository task. That does
not waive the known evaluator defect; it changes the next useful experiment.

## Limit

Do not use “question the premise” to evade an unmet requirement. Do not build
three prototypes when the existing owner and acceptance test already determine
the correct small change.
