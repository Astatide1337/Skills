---
name: systematic-debugging
description: Diagnose an unexplained bug, failure, regression, runtime error, or performance problem before fixing it. Find and verify the root cause; do not guess.
---

# Systematic Debugging

Find the cause before fixing the symptom.

## Workflow

1. **State the exact failure.**
   - Describe what happened, where, and what was expected instead.
   - Keep observed facts separate from explanations.

2. **Reproduce it.**
   - Reproduce the same failure in the closest practical environment.
   - Record the exact command, request, user flow, or conditions that trigger it.
   - If it cannot be reproduced, gather current logs/state before changing anything.
   - Invest disproportionate effort in a tight feedback loop that fails on the user's exact symptom. Prefer, in order: a focused test, request/CLI fixture, browser script, captured-trace replay, throwaway harness, fuzz loop, bisection, or differential comparison.
   - Tighten the loop until it is fast, deterministic, and runnable without interpretation. For flaky bugs, raise and measure the reproduction rate instead of waiting for a perfect repro.
   - Run at least one command, request, or interaction capable of producing the
     failure before calling it reproduced. A plausible test plan is not a red
     state.
   - Minimize the reproduction. Remove inputs, services, timing, and setup one
     at a time until every remaining element is load-bearing. Record what can
     be removed without changing the failure.

3. **Inspect the real system.**
   - Read the relevant code, configuration, tests, logs, runtime state, and recent changes.
   - Check the actual branch, environment, dependencies, network/topology, and data state when relevant.
   - Do not assume local, CI, staging, and production behave the same.

4. **List facts and unknowns.**
   - Write a short `Known` and `Unknown` list.
   - Treat anything not directly observed as an assumption.

5. **Form competing hypotheses.**
   - Prefer three to five plausible causes when the evidence permits; use fewer
     when the search space is genuinely narrow.
   - Rank them by current evidence, not intuition alone.
   - Write each as: `If H is true, observation O should occur; observation R
     would reject it.`

6. **Run the cheapest discriminating check.**
   - Choose the check that best separates the hypotheses.
   - Name one smallest next experiment first: exact input or cohort, observation,
     and how each possible result changes the next step. Put broader follow-up
     checks after it rather than presenting an undifferentiated investigation list.
   - Give that first experiment a red-capable procedure: the exact action that
     can exhibit the user's symptom, how many repetitions or what time window
     will measure it, and the observation that counts as failure. Then state
     which elements to remove while preserving the failure to minimize the
     reproduction.
   - Change only diagnostic state when necessary; avoid behavior-changing fixes at this stage. Mark temporary logs, probes, flags, and fixtures so their removal is verifiable.
   - If evidence contradicts the current explanation, discard the explanation.

7. **Establish the root cause.**
   - Do not proceed because a hypothesis merely "sounds right."
   - Require evidence connecting the cause to the observed failure.

8. **Apply the smallest fix.**
   - Fix the identified cause without unrelated cleanup, refactors, or architecture changes.
   - Preserve existing conventions unless they are part of the demonstrated cause.

9. **Verify against the original failure.**
   - Re-run the exact reproduction.
   - Run the smallest relevant regression checks.
   - Confirm the mechanism is fixed, not merely hidden.
   - Remove temporary instrumentation and preserve the minimized reproduction as a regression test when it exercises the real failure seam.
   - If the minimized reproduction cannot become a stable test, identify the
     narrowest seam that can assert the broken invariant and explain the gap.
   - Record the prevention follow-up when the failure exposed a missing alert,
     invariant, deployment check, or operational runbook.

## Stop conditions

Stop and investigate further if:

- the proposed fix depends on an unverified assumption;
- the environment differs materially from the reproduction;
- a new failure appears that the current explanation does not account for;
- the task reaches production or production-like state where `production-safety` applies.

## Avoid

- Trying several fixes at once.
- Increasing timeouts or retries without explaining the delay/failure mechanism.
- Refactoring around a symptom.
- Treating a local success as proof of CI or deployed behavior.
- Repeating a failed action without learning new information.
- Declaring root cause from an error message alone.

## Report

When the debugging task is complete, report:

- **Root cause:** the supported mechanism.
- **Evidence:** what established it.
- **Fix:** what changed.
- **Verification:** how the original failure was re-tested.
- **Uncertainty:** anything material that remains unverified.

## Output-shape discipline

For a text-only diagnosis, make the conditional structure explicit: write
`If <observed result>, then <next check>` (or an equivalent clearly conditional
branch) for each material hypothesis.

## Execution boundary

Match the task's requested mode and the tools it authorizes.

- For prompt-only tasks that explicitly forbid workspace or tool use, use only
  the supplied text. `Review-only`, `diagnose`, and `do not edit` prohibit
  mutation, not observation: inspect in-scope supplied files with read-only
  tools unless the user also forbids that inspection. If required evidence is
  absent after checking the declared scope, identify the smallest artifact needed.
- For workspace-write requests, read only declared inputs and write only the declared output paths. Do not broaden the scope, probe credentials, inspect evaluator or harness metadata, or use network/MCP unless the task explicitly authorizes it.
- Never claim that a command, file change, deployment, or verification happened unless it actually happened and is supported by observed evidence.
