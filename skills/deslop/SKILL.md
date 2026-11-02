---
name: deslop
description: "Removes redundant comments, dead code and needless abstraction from a diff. Use for code cleanup or observed clutter during review. Not for every commit, prose (unslop) or redesign."
---

# Deslop

Remove clutter from generated code before review or commit. Preserve behavior
and keep the cleanup within the requested change.

## Inspect the change

- Establish the comparison base. Read the complete diff, affected callers and
  nearby code to understand the repository's style.
- Distinguish redundant generated additions from intended behavior, input
  validation, security comments and project conventions.
- Handle correctness defects through the implementation workflow. Do not
  disguise a behavior change as cleanup.

## Focus the cleanup

- Remove comments that restate obvious code or conflict with nearby style.
  Keep explanations of non-obvious invariants, security rules and operational
  constraints.
- Remove a defensive check or `try`/`except` only when the surrounding code's
  contract makes it redundant. Preserve validation and error handling where
  input is untrusted or crosses an external interface.
- Replace an `any` cast used to silence a type error when existing types or
  a narrow type guard can express the same contract.
- Use early returns to remove needless nesting when control flow and error
  behavior remain clear.
- Match nearby naming, structure and formatting. Do not rewrite untouched
  files or add a dependency for cosmetic cleanup.

## Verify and hand off

Run the relevant existing tests, type checks or formatter. If cleanup exposes
an out-of-scope bug, stop the cleanup and use systematic debugging; do not
silently change behavior. An explicitly in-scope bug can continue through its
implementation workflow.

Compare the final diff and public behavior with the pre-cleanup version.
Report the checks that ran and any verification gap that matters. Keep useful
comments and safeguards even when their style resembles generated code.
