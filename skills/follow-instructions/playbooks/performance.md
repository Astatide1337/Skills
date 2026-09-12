# Performance / measure or improve

## When

Use when the user asks to diagnose slowness, establish a performance baseline,
or improve a measured bottleneck. Measurement-only work must not edit the
system.

## Inputs to establish

- user-visible symptom, representative workload/data, correctness constraints,
  environment, and metric (including tail/resource limits);
- repeatability, noise budget, and finite experiment/repetition budget;
- `measure` versus `improve` authority and rollback for an optimization.

Use [`hillclimb`](../../hillclimb/SKILL.md) for controlled repeated tuning and
[`systematic-debugging`](../../systematic-debugging/SKILL.md) when an unexplained
failure, not merely a slow result, is being diagnosed.

## Steps and decision points

1. Confirm the metric measures the stated problem and capture a comparable,
   repeatable baseline with workload, versions, and data recorded.
2. Inspect traces, profiles, queries, or existing instrumentation to identify
   the actual bottleneck. Do not optimize a suspicious line without evidence.
3. In measure mode, return findings and the next experiment without mutation.
   In improve mode, change one relevant mechanism and keep functionality and
   security constraints fixed.
4. Re-run the same workload enough to distinguish signal from noise. Check
   latency tails, errors, resource use, and correctness, not only a favorable
   average. Retain a change only after the declared win is reproduced.

## Failure and recovery

If the workload is unrepresentative, metric unavailable, or results vary beyond
the declared budget, report inconclusive and stop optimization. Do not lower
correctness, alter the workload, discard unfavorable runs, or silently compare
different budgets. Undo only run-owned rejected changes.

## Completion evidence

Provide baseline/candidate measurements under the same conditions, relevant
correctness results, resource/tail effects, repetitions and uncertainty. A
single faster command or benchmark setup is not an improvement claim.

## Example

Measure a slow query with a fixed fixture, inspect its plan, add the smallest
index or query change, and compare median and p95 plus result equivalence.

## Near-miss

“Make this endpoint faster” without a representative request or allowed
workload is blocked at measurement; guessing a cache is not diagnosis.
