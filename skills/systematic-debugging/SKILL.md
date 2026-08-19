---
name: systematic-debugging
description: Use this skill whenever a bug, failing test or CI job, runtime error, regression, broken integration, performance problem, or other unexpected behavior has an unknown or uncertain cause. Diagnose the real root cause before changing behavior; do not jump from a plausible explanation to a fix. Use even when the likely fix seems obvious if the failure has not been reproduced and explained.
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

3. **Inspect the real system.**
   - Read the relevant code, configuration, tests, logs, runtime state, and recent changes.
   - Check the actual branch, environment, dependencies, network/topology, and data state when relevant.
   - Do not assume local, CI, staging, and production behave the same.

4. **List facts and unknowns.**
   - Write a short `Known` and `Unknown` list.
   - Treat anything not directly observed as an assumption.

5. **Form competing hypotheses.**
   - Prefer a small set of plausible causes.
   - For each hypothesis, identify evidence that would support or reject it.

6. **Run the cheapest discriminating check.**
   - Choose the check that best separates the hypotheses.
   - Change only diagnostic state when necessary; avoid behavior-changing fixes at this stage.
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

- For text-only, plan-only, or review-only requests, use the supplied prompt and explicitly provided context. Do not inspect the workspace, run shell/CLI commands, call network/MCP/browser tools, or edit files. If required context is missing, say so and identify the smallest artifact needed.
- For workspace-write requests, read only declared inputs and write only the declared output paths. Do not broaden the scope, probe credentials, inspect evaluator or harness metadata, or use network/MCP unless the task explicitly authorizes it.
- Never claim that a command, file change, deployment, or verification happened unless it actually happened and is supported by observed evidence.
