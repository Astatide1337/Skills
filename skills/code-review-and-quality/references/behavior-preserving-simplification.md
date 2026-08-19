# Behavior-preserving simplification

Treat current observable behavior as the contract unless the task explicitly changes it.

1. Identify the behavior and relevant tests.
2. Establish a passing baseline.
3. Remove dead paths, duplicate branches, pass-through wrappers, needless configuration, and abstractions that hide no complexity.
4. Prefer one obvious data flow and one source of truth.
5. Make one conceptual change at a time.
6. Re-run the same checks after every meaningful reduction.

Stop when further shortening would obscure intent, collapse a useful boundary, or require a behavior change.
