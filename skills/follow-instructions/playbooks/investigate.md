# Investigate / read

## When

Use for read-only diagnosis, research or explanation of a repository, service,
document, log or other supplied source. A pasted snippet that is sufficient on
its own stays a direct answer.

## Inputs to establish

- the exact question, requested answer shape, source/revision and search limits;
- expected versus observed behavior, environment, and relevant time window;
- whether the user wants only findings or a follow-on artifact such as an issue;
- what may be inspected and any explicit no-edit or no-network rule.

Use [`systematic-debugging`](../../systematic-debugging/SKILL.md) for causal
bugs, [`how`](../../how/SKILL.md) for source flow, [`why`](../../why/SKILL.md)
for history, and native web/search tools only when
external research is requested or needed for an uncertain primary source.

## Steps and decision points

1. Locate the named revision, owner, implementation, callers, configuration,
   and direct evidence before relying on a summary or error message.
2. Separate `Known`, `Unknown`, and hypotheses. For a causal claim, state at
   least one plausible competing explanation and the smallest observation that
   distinguishes it. For capability discovery, resolve the effective
   configuration and target identity; verify names and prior-session assumptions
   against the current target. An absent conventional endpoint does not
   establish an absent API: inspect the owning source or existing client before
   escalating. Keep discovery bounded to the authorized target and metadata; do
   not print credentials or enumerate unrelated secrets.
3. Run that read-only check in the closest authorized environment. If it
   contradicts the hypothesis, update the explanation rather than forcing the
   result. Use a disposable reproduction only when authorized.
4. Follow primary source passages, logs, or traces to the requested answer.
   A diagnosis states the cause supported by the evidence, the intended behavior
   and any unresolved explanation. Exploration gives viable options, a recommendation and
   material unknowns before asking for a choice. If implementation is requested,
   hand nontrivial work to [design](design.md) and the
   [approved-plan contract](../references/approved-plans.md). A read-only
   diagnosis or requested issue artifact does not authorize a source fix.

## Failure and recovery

If a source is missing, truncated, stale, or inaccessible, try one authorized
alternative and state the gap. An empty search is not proof that no consumer or
cause exists. Stop repeated retrieval without new evidence. Never turn a
plausible mechanism into a confirmed diagnosis.

## Completion evidence

Return the direct answer, source locations or observations, desired behavior,
which hypotheses the evidence ruled out, remaining uncertainty, and the next
check if one is needed.
For exploration, include the options and actionable recommendation. A diagnosis is
not a fix, and a command that exited successfully is not proof of runtime
behavior. For offline service snapshots, explicitly mark live reachability and
authentication untested; discovering an interface does not exercise it.

## Example

“Why does this tenant lookup return another user's row?” reads the lookup,
scope predicate, caller, and two-tenant fixture, then reports the observed
authorization gap without editing code.

## Near-miss

“Explain this pasted function in two sentences; do not inspect files” uses only
the supplied function and does not crawl a repository, create notes, or propose
unrequested refactoring.
