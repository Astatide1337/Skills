# Behavior-preserving simplification

Treat current observable behavior as normative where the task preserves it.
For approved new behavior, use the
[approved-plan contract](../../follow-instructions/references/approved-plans.md)
and its acceptance, interfaces, owners and permitted effects.

1. Identify the behavior, approved boundaries and relevant tests.
2. Establish current evidence, distinguishing existing failures from the
   acceptance required of the new behavior; do not invent a passing baseline.
3. Remove dead paths, duplicate branches, pass-through wrappers, needless configuration, and abstractions that hide no complexity.
4. Prefer one obvious data flow and one source of truth.
5. Make one conceptual change at a time.
6. Re-run the same checks after every meaningful reduction.

Stop when further shortening would obscure intent, collapse a useful boundary, or require a behavior change.
Reviewer-driven reductions are allowed only within the approved contract.
Material architecture, ownership, public-interface, scope or verification
changes need a revised HTML plan and renewed confirmation. Preserve failed and
unavailable checks rather than weakening acceptance to permit the reduction.
