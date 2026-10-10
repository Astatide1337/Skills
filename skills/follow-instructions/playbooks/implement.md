# Implement / bug, feature, refactor

## When

Use when the requested outcome changes repository behavior or structure. Pick
`bug`, `feature`, or `refactor`; add a PR route only when publication is also
requested or included in approved delivery. Mechanical local changes use the
coordinator's short path instead. Nontrivial feature/issue work starts with the
[approved-plan contract](../references/approved-plans.md) and [design](design.md)
when its confirmed plan is missing.
Use [`systematic-debugging`](../../systematic-debugging/SKILL.md) for unclear causes, [`architect`](../../architect/SKILL.md) for unclear boundaries,
[`web-interface`](../../web-interface/SKILL.md) for UI, and
[`code-review-and-quality`](../../code-review-and-quality/SKILL.md) before
handoff.

## Inputs to establish

- expected/observed behavior, exact acceptance and negative cases;
- current branch/revision, owning implementation, callers, data/state owners,
  fixtures, commands, and relevant environment;
- allowed files/effects, compatibility constraints, and requested publication;
- approved plan/prototype version and digest, user confirmation, exclusions and
  outstanding evidence gates for nontrivial work;
- for a sensitive boundary, identities, consumers, secret data, and rollback.

## Steps and decision points

1. Inspect the owner and run the original reproducer on the pre-change state
   when claiming a bug fix. Record facts separately from assumptions. A feature
   or refactor starts from its own observable contract; it does not need an
   incident reproducer.
   Recovery from an unavailable historical runner retains this order: inspect
   a safe available equivalent, reproduce on unchanged code, then repair and
   rerun the preserved acceptance. Reading checks alone is not reproduction.
2. For a bug with material causal uncertainty, list competing causes and run
   the cheapest discriminating check; an observed obvious cause needs no invented
   alternatives.
   For a feature, define observable states and extend existing interfaces. For
   a refactor, state behavior/contracts that must remain unchanged.
3. Choose the smallest correction or coherent feature sequence. Preserve
   architecture and compatibility; do not add speculative abstractions. When
   changing boundary data or shared state, apply [construction decisions](../references/principles/ownership-and-domain.md#construction-decisions-and-counterexamples);
   an already-clear local edit needs no extra design procedure. Reuse the
   approved behavior, interfaces and owners; resolve material deviations through
   the shared contract before dependent implementation.
4. Implement one unit at a time. Add a focused regression or acceptance check
   that asserts the outcome, including a relevant negative control.
5. Re-run the original path and affected native/supplemental checks; exercise
   the real UI/API/CLI when relevant through its actual tools. Obtain independent
   review of approved nontrivial delivery, fix in-scope findings and refresh
   affected checks and reviewer coverage on the final artifact.
6. Finish the whole approved result, including a scoped final commit when
   approval covers it. When
   publication is approved, use [pull-requests](../../pull-requests/SKILL.md) for
   a draft PR/MR, in-scope fixes and current-head CI readiness. A draft may be
   needed to obtain CI before readiness; never merge or enable auto-merge.

## Failure and recovery

If the baseline or reproducer is unavailable, report that counterfactual gap
and use the strongest safe alternative; do not fabricate a before/after win.
If a check contradicts the hypothesis, return to diagnosis. Remove temporary
probes and revert only run-owned rejected changes. Do not broaden secret access
or hide a symptom to make a test pass.
Preserve evidence for material discoveries, stop the dependent unit and revise
its HTML plan before resuming; continue independent approved units. Diagnose
safe alternatives and recoverable setup before declaring a blocker. Repeated
failure or no new evidence uses [self-reflect](../../self-reflect/SKILL.md).

## Completion evidence

Report the mechanism, changed owner, original reproduction result, focused
regressions, final diff scope, and unverified environments. State whether the
result is a source change, local behavior, or published artifact. Include the
approved plan identity, final review and current-head evidence when required;
report an unavailable gate explicitly instead of stopping at a partial result
with a readiness claim. Do not claim
deployment or user-visible success from a build alone.

## Example

For a wrong-tenant lookup, reproduce both tenants, scope the lookup to the
authenticated tenant, add the cross-tenant denial regression, and re-run both
allowed and denied requests.

## Near-miss

“Refactor this parser without changing behavior” does not add validation or a
new feature merely because the old code looks awkward; it compares existing
callers and behavior before reporting the structural simplification.
