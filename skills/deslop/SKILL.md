---
name: deslop
description: When a diff contains AI-generated code clutter.
---

# Deslop

Simplify the requested change while preserving its behavior and safeguards.
Use this during implementation or for a requested cleanup; an ordinary change
needs one useful pass, not a mandatory series of reviews.

## Prefer existing capability

Before adding code, inspect what already solves the problem: existing project
code, the standard library, native platform features, and installed dependencies.
Add custom implementation only for the remaining requirement. Remove speculative
flexibility and duplicate wrappers when their callers establish that they are
unnecessary. A shorter implementation is better only when it remains correct,
readable, and complete.

This adapts the decision ladder from [Ponytail](https://github.com/DietrichGebert/ponytail)
without its always-on hooks, output restrictions, or extra command runtime.

## Inspect the change

- Pin the comparison base and inspect the complete diff, affected callers, and
  the repository's local style.
- Separate generated additions from intentional behavior, boundary checks,
  security comments, and project conventions.
- Keep a possible correctness defect in the owning implementation's workflow;
  do not hide it as cleanup.

## Focus the cleanup

- Remove comments that narrate obvious code or conflict with the surrounding
  style. Keep comments that explain a non-obvious invariant, security rule, or
  operational constraint.
- Remove a defensive check or `try`/`except` only when the surrounding
  contract makes it redundant and the behavior remains unchanged. Preserve
  validation and error handling at untrusted or external boundaries.
- Replace an `any` cast used only to silence a type error when the existing
  types or a narrow type guard express the same contract.
- Flatten needless nesting with early returns when it keeps control flow and
  error behavior clear.
- Match nearby naming, structure, and formatting. Do not rewrite untouched
  files or add a dependency to make the diff look cleaner.

## Verify and hand off

- Run the focused tests, type checks, or formatter relevant to the changed
  code when they exist. If cleanup exposes a bug, stop and route it through
  systematic debugging rather than silently changing behavior.
- Re-read the final diff and compare the public behavior with the pre-cleanup
  version. Report only checks that actually ran.
- Keep the final summary to one to three sentences.

Guardrails: preserve behavior unless a clear bug is explicitly in scope, prefer
minimal focused edits, and do not remove useful comments or safeguards merely
because they resemble generated code.
