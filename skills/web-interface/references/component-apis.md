# Component APIs

Read this when designing a reusable component or refactoring an API with prop
sprawl, shared child state, or awkward customization.

## Decide before refactoring

1. Preserve booleans that represent independent state or a stable public
   contract. Replace presentation or slot booleans only when composition makes
   the caller clearer.
2. Use explicit variants for a small, finite visual set. Use `children` or
   named slots for structural variation. Do not add a render prop unless the
   child genuinely needs invocation arguments.
3. Use a compound component and shared context only when several cooperating
   parts need shared state or coordinated semantics. Keep state ownership and
   the public component contract explicit.
4. Choose controlled versus uncontrolled behavior deliberately. Expose one
   predictable source of truth, accessible labels/states, and a migration path
   when changing public behavior.
5. Verify the project's React version and support policy before adopting
   version-specific APIs. Do not blindly replace `useContext`, `forwardRef`, or
   public ref contracts because an example targets a newer React release.

## Preserve the contract

- Keep semantic HTML, keyboard behavior, focus management, and error states
  intact through the refactor.
- Prefer a local implementation simplification over a breaking public API
  change. When a breaking change is intentional, document the before/after
  call site and migration.
- Stop when composition makes the common case harder than the original API.
