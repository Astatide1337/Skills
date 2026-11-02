# Behavior-preserving simplification

When the task requires a behavior-preserving cleanup, retain the current
observable behavior.
For approved new behavior, use the
[approved-plan contract](../../follow-instructions/references/approved-plans.md)
for the required behavior, interfaces, owners and permitted actions.

1. Identify the behavior, approved boundaries and relevant tests.
2. Run the current checks. Distinguish existing failures from requirements the
   new behavior must satisfy; do not assume the baseline passes.
3. Remove dead paths, duplicate branches, pass-through wrappers, needless configuration,
   and abstractions that hide no complexity.
4. Prefer one obvious data flow and one source of truth.
5. Make one conceptual change at a time.
6. Re-run the same checks after every meaningful reduction.

Stop when further shortening would obscure intent, collapse a useful boundary, or
require a behavior change.
Reviewer-driven reductions are allowed only within the approved contract.
When a reduction changes architecture, ownership, a public interface, scope or
verification, reassess it through the actual
[plans and authority contract](../../follow-instructions/references/approved-plans.md).
Ask again only when the user or project requires approval, the proposed action
exceeds the approval already given, or required permission is missing. Continue
authorized simplification without adding an HTML approval step. Retain failed
and unavailable checks; do not weaken them to accept the shorter code.
