---
name: hillclimb
description: Improve one measurable outcome through repeated controlled experiments. Use when asked to optimize, tune, beat a baseline, raise or lower a metric, compare variants empirically, or keep improving until a target is reached. Do not use for ordinary bug fixes, one-pass implementation, subjective improvement with no repeatable evaluation, or production experiments whose safety and authorization are not established.
---

# Hillclimb

Improve the measured result without sacrificing the system around it.

## Establish a trustworthy ruler

Before changing the candidate:

1. Name one primary metric, its direction, the representative workload, and a
   checkable target or experiment budget.
2. Name the non-regression gates: correctness, safety, quality, resource use,
   or complexity constraints that a metric win must preserve.
3. Run and record the unchanged baseline with the same command and environment
   that will measure candidates.
4. Check that the measurement is repeatable and sensitive enough to distinguish
   a meaningful change from noise. Use repeated samples and a declared summary
   statistic when the result varies.
5. Freeze the workload, metric calculation, and gates for the run. If the ruler
   is defective, repair it and discard earlier comparisons rather than changing
   it after seeing an inconvenient result.

Do not optimize a proxy without explaining why it represents the requested
outcome. Keep final evaluation cases separate from the examples used to choose
changes.

## Run controlled experiments

Maintain a compact decision log with:

`attempt | hypothesis | change | before | after | gates | decision | note`

Use an existing experiment log when the project has one. Otherwise keep the log
in the response or a temporary location unless the user requests a repository
artifact.

For each attempt:

1. Read the current accepted state and previous results.
2. State a mechanism-based hypothesis and the result that would support or
   reject it.
3. Change one meaningful variable when practical. If variables must move
   together, explain why the combination is indivisible.
4. Run the frozen measurement and every relevant non-regression gate.
5. Keep the candidate only when improvement exceeds measurement noise and all
   gates pass. Otherwise revert the attempt completely before continuing.
6. Record rejected and neutral attempts so the search does not circle back to
   them.

Do not stack unmeasured changes, retain a neutral change because it looks
promising, or claim improvement from source inspection. The observed result
decides.

## Search without overfitting

- Prefer hypotheses grounded in the system's actual bottleneck or failure mode
  over random parameter sweeps.
- Use tuning workloads to choose changes. Exercise the retained result once on
  untouched representative cases before making a general claim.
- Treat the untouched check as a verdict, not another tuning observation. If
  the selected candidate fails it, do not promote an untested runner-up using
  the same evidence. Restore the original baseline or the last state that was
  independently validated and report that no general win was established. To
  continue searching, reserve a new untouched set before tuning resumes.
- Track secondary metrics and important cohorts. An average gain that hides a
  severe regression is not a win.
- Compare candidates against the latest accepted state and preserve the original
  baseline for the final delta.
- Treat simpler candidates as better when results are materially equivalent.
- Never weaken a regression gate, edit expected outputs, discard an unfavorable
  cohort, or tune the evaluator merely to manufacture a win.

For performance work, control environmental noise before attributing small
differences to the change. For qualitative work, define an anchored rubric and
use blinded or consistently ordered comparison when practical.

## Stop deliberately

Stop when the target or experiment budget is reached, remaining hypotheses are
not worth their cost, the measurement cannot support a conclusion, or a safety
boundary prevents further experiments. A plateau is evidence to reconsider the
mechanism, not permission to relax the target.

Before finishing, restore rejected work, run the non-regression gates on the
retained state, and evaluate the untouched cases once. Do not call a tuning win
the final result when that evaluation rejects it. Use `verify-work` to
match the final claim to the evidence. Use `production-safety` before any
production or production-like experiment.

Report:

- primary metric, workload, target, and gates;
- baseline and final result with absolute and relative change;
- attempts run, kept, and rejected;
- retained changes and their supported mechanisms;
- untouched-case result and material regressions or uncertainty;
- when untouched evaluation rejects the winner, the candidate's delta labeled
  as invalidated and the restored state reported explicitly;
- why the run stopped and the best remaining hypothesis, if any.
