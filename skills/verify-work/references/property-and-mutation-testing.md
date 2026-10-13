# Property and mutation testing

Use when important invariants have broad inputs, state sequences or weak tests.
Prefer existing example/regression checks for a clear local correction.

## Property checks

Name an independently meaningful invariant before choosing a library: parse and
serialize round trips, idempotent normalization, conservation across transfers,
tenant isolation or equivalent results under supported operation ordering.
Define valid input constraints and meaningful boundaries; don't restate the
implementation as an oracle. Keep a failing seed/example and turn important
counterexamples into readable regressions.

Use an existing property library first. Consider language-appropriate
[fast-check](https://fast-check.dev/) or
[Hypothesis](https://hypothesis.readthedocs.io/) only when the gap merits a
project-scoped dependency and runner integration. A generated-input pass proves
only the exercised property under that generator and environment.

## Mutation checks

Use a targeted trial on a consequential module when passing tests may fail to
detect wrong behavior. Run the ordinary suite first. With a suitable existing
runner, [StrykerJS](https://stryker-mutator.io/docs/stryker-js/introduction/) can
alter code and report which changes tests detect. Inspect surviving mutations:
some are equivalent or outside the contract; others expose missing assertions.
Do not target a universal score, weaken assertions or add tests mirroring code
just to kill mutations. Record the useful defects or strengthened assertions
against execution cost and flakiness; keep mutation suites off ordinary tasks.

These are original adoption guidance, with upstream documentation linked for
mechanics. Select and recheck versions through the shared tool-selection policy;
no installation or broad test mandate follows from reading this reference.
