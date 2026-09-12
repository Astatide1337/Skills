# Cause and behavior

This local reference combines pstack's Fix Root Causes, Prove It Works, and
Test Behavior Not Implementation. It supplements, rather than replaces,
`systematic-debugging` and `verify-work`.

## Trigger

Use for a bug, regression, unexplained result, conflicting review finding, or
any completion claim about a behavior.

## Decision rule

Preserve the failure, distinguish facts from hypotheses, and run the smallest
observation that separates plausible causes. Correct the owner of the cause.
Test the behavior through the path a user or caller exercises, including a
relevant negative control. Do not use source fragments, self-attestation, a
mocked boundary, or a passing build as proof of an untested runtime behavior.

## Procedure

1. Preserve or recreate the original failure before editing when the
   environment permits.
2. Inspect the implementation, callers, state, and boundary that own it.
3. State the current hypothesis and one plausible alternative when uncertainty
   is material. Run a discriminating check rather than guessing.
4. Make the smallest owner-level correction and keep the original regression.
5. Exercise the real input-to-output path. Assert a literal observable result,
   not only that a function was called or that a fixture exists.
6. Run the relevant negative case and inspect the final artifact after tests,
   cleanup, and delegated work.

## Principal-engineer lens

The reusable skill is causal explanation. A high-level engineer can show why
the system failed, why this owner is responsible, and which evidence would
falsify the explanation. That narrative prevents symptom fixes from becoming
architecture.

## Evidence

Record the unchanged reproducer, the discriminating observation, the changed
owner, and the behavior-level result. If a required baseline or integration is
unavailable, report it as a limitation rather than inventing a pass.

## Example

Run the unchanged pagination traversal, inspect the cursor owner, correct the
last-returned-record cursor, and verify complete traversal with filters and
tenant isolation. A test that only searches for `PermissionError` in source
text proves nothing about runtime behavior.

## Limit

Do not manufacture competing hypotheses for a mechanical change with one
obvious owner. Do not require an application browser session for a backend
function when the relevant behavior is already directly exercised by its real
project test path.
