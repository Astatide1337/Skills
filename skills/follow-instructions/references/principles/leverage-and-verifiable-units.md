# Leverage and verifiable units

Adapted from pstack's Build the Lever, Sequence Verifiable Units, Guard the
Context Window, and Encode Lessons in Structure.

## Trigger

Use for non-trivial repeated work, multi-step changes, large outputs, context
pressure, parallel delegation, or a correction that has appeared more than once.

## Decision rule

Build the smallest rerunnable artifact that performs or proves repeated work.
Break changes into units that each end in a check. Give independent workers
separate ownership and ask each for evidence, then inspect the integrated result.
Put a recurring correction in the simplest mechanism that can enforce it.

## Procedure

1. Complete one unit directly to learn the real recipe.
2. If the work outlives the session or repeats, choose a script, test, schema,
   or skill that makes the operation and its proof rerunnable. Do not build a
   framework for a one-off.
3. Order units so each has a known-good start, one bounded change, and a
   focused check before the next unit begins.
4. Isolate large payloads and keep summaries in the coordinating context. Read
   only material needed for the current decision.
5. When delegating, specify the owned files/state, interface, authority,
   evidence, and do-not-touch boundary. Verify the artifact, not the worker's
   report.
6. If the same correction recurs, move it into a deterministic check, metadata
   rule, or canonical owner instead of repeating prose.

## Evidence

Keep the script, test, or structural guard visible when it carries the proof.
Show the per-unit checks and the final integrated check. Report context or
resource limits instead of hiding them behind a summary.

## Example

For a repeated migration across known callers, migrate one caller, run its
contract test, then commit a small deterministic check before proceeding. Do
not ask several agents to hand-edit the same shared file.

## Limit

A trivial, visible edit needs no reusable tool. Execute serially when the dependency
chain is small or delegation would cost more context than it saves.
