# Which examples should the next contributor copy?

Before copying an example, follow it to the supported entry point. Compare its
purpose, callers and constraints with the current task. A repeated snippet,
comment or template can outlive the decision that produced it. When examples
disagree, check the owning contract, tests, or decision history.

## When a workaround keeps appearing

Compare the failing paths and a similar path that works without the workaround.
What does each caller have to guess, retry, or synchronize? Reproduce the
failure that the workaround masks. For example, a delay after every save may
be compensating for a missing completion signal. Make completion observable at
the writer, then exercise a slow save. Keep a timer used for a real user-facing
debounce if it still serves that separate purpose.

If a low-level operation requires the same delicate sequence at many call
sites, expose the supported operation at the layer that can guarantee the
sequence. Show a real caller using it and a legitimate low-level use inside
the implementation. This can be as small as an existing transaction helper
that commits or rolls back for the caller.

## Keep the supported path visible and enforceable

- Express an architectural boundary in the module layout, exports or build
  targets so contributors can find the intended entry point. Use the project's
  dependency checker, compiler visibility, import rule or contract test to
  reject forbidden crossings. Check indirect routes such as re-exports when
  the constraint is about runtime dependencies.
- First demonstrate that the project check rejects a new violation and accepts
  a legitimate neighbor. Then migrate in-scope existing occurrences, including
  scaffolds, examples and fixtures that teach the old pattern. Exercise the
  replacement through a real consumer. Preserve deliberate compatibility
  paths and negative-test fixtures. If adoption must be staged, bound any
  allowance to the identified legacy users; verify a new user still fails.
- Write the diagnostic for the person fixing the violation. Identify the
  offending location or operation, the constraint it breaks, and the supported
  replacement or recovery. Trigger it through the normal build or check;
  follow its advice and verify the formerly failing example now passes.

## Scope corrections and exceptions

Before turning a correction into persistent guidance, state the condition that
made the original behavior wrong. Look for a valid exception. If the boundary
has none, test a permitted neighboring behavior, such as importing a shared
module from the renderer.
Keep a local preference or temporary constraint with its owner. A broader rule
needs evidence that the same condition applies across the proposed scope.

Treat an exception comment as a claim. Trace it to the dependency, supported
behavior or owner decision it cites. Preserve useful rationale for verified
exceptions and keep their scope narrow. If the premise has expired, repair
the workaround and remove its stale justification together. Within a read-only
review, report the evidence, concrete repair and permitted behavior to preserve.
