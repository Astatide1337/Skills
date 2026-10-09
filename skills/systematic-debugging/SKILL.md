---
name: systematic-debugging
description: When causes are unclear, evidence conflicts or fixes keep failing.
---

# Systematic Debugging

Find the cause before fixing the symptom. An obvious mechanical correction
with a clear owner and focused reproducer uses `follow-instructions`' short
path; do not manufacture a multi-hypothesis investigation for it.

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
   - If a setup or tool fault is recoverable within scope, repair it and rerun
     the original check. If an external write has an uncertain result, observe
     the same object by stable identity before any retry; never infer failure
     from a timeout alone.

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
   - Preserve the failing input, observed output, and cleanup evidence. Do not
     turn a failed assertion into a skip or narrow the expected result merely
     to obtain a passing check.

For an HTTP/RPC request mismatch or a proposed API contract change, use the
[API/backend contract procedure](references/api-backend-contracts.md) within
this workflow. Keep the exact caller path and contract provenance in view; a
smoke mock alone does not establish wire behavior.

For a Linux, network, or container incident whose failing layer is unclear,
use the [Linux/network/container procedure](references/linux-network-container-incidents.md)
to compare name resolution, route, namespace, listener, and protocol evidence.

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

Apply the shared [execution boundary](../follow-instructions/references/principles/authority-and-claims.md#execution-boundary).
Keep the task-specific restrictions above; this skill grants no additional effects.
