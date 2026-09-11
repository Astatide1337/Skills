# Implement / bug, feature, refactor

## When

Use when the requested outcome changes repository behavior or structure. Pick
`bug`, `feature`, or `refactor`; add a PR route only when publication is also
requested. Use [`systematic-debugging`](../../systematic-debugging/SKILL.md) for
bugs, [`architect`](../../architect/SKILL.md) for unclear boundaries,
[`web-interface`](../../web-interface/SKILL.md) for UI, and
[`code-review-and-quality`](../../code-review-and-quality/SKILL.md) before
handoff.

## Inputs to establish

- expected/observed behavior, exact acceptance and negative cases;
- current branch/revision, owning implementation, callers, data/state owners,
  fixtures, commands, and relevant environment;
- allowed files/effects, compatibility constraints, and requested publication;
- for a sensitive boundary, identities, consumers, secret data, and rollback.

## Steps and decision points

1. Inspect the owner and run the original reproducer on the pre-change state
   when claiming a bug fix. Record facts separately from assumptions.
2. For a bug, list competing causes and run the cheapest discriminating check.
   For a feature, define observable states and extend existing interfaces. For
   a refactor, state behavior/contracts that must remain unchanged.
3. Choose the smallest correction or coherent feature sequence. Preserve
   architecture and compatibility; do not add speculative abstractions.
4. Implement one unit at a time. Add a focused regression or acceptance check
   that asserts the outcome, including a relevant negative control.
5. Re-run the original path and affected checks, exercise the real UI/API/CLI
   when relevant, then review the diff and callers. A PR follow-on begins only
   after the implementation is ready.

## Failure and recovery

If the baseline or reproducer is unavailable, report that counterfactual gap
and use the strongest safe alternative; do not fabricate a before/after win.
If a check contradicts the hypothesis, return to diagnosis. Remove temporary
probes and revert only run-owned rejected changes. Do not broaden secret access
or hide a symptom to make a test pass.

## Completion evidence

Report the mechanism, changed owner, original reproduction result, focused
regressions, final diff scope, and unverified environments. State whether the
result is a source change, local behavior, or published artifact. Do not claim
deployment or user-visible success from a build alone.

## Example

For a wrong-tenant lookup, reproduce both tenants, scope the lookup to the
authenticated tenant, add the cross-tenant denial regression, and re-run both
allowed and denied requests.

## Near-miss

“Refactor this parser without changing behavior” does not add validation or a
new feature merely because the old code looks awkward; it compares existing
callers and behavior before reporting the structural simplification.
