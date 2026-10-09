# Python and data lifecycle debugging

## Trigger

Use this procedure when a Python job, API handler, importer, query, or migration
stores, drops, duplicates, reorders, or returns stale data. Use the
[API/backend contract procedure](api-backend-contracts.md) as well when the
failure crosses an HTTP or RPC contract. Use the
[state and lifecycle boundaries](../../architect/references/state-and-lifecycle.md)
for owned state, commit, retry, or cancellation decisions, and the
[`migrate-operate` procedure](../../follow-instructions/playbooks/migrate-operate.md)
for production-like stores or planned migrations.

## Procedure

1. **Preserve the failure.** Save the smallest input that still shows the
   missing, duplicate, stale, malformed, or misordered result. Keep its types,
   nulls, key values, duplicate count, order, and relevant time boundaries. Redact
   private values without changing those properties. Record the expected and
   observed rows or values before normalizing the input.
2. **Trace the data owner path.** Follow the input from parser and boundary
   validation through transformation, transaction or batch writer, durable
   store, query, and response. Name the canonical key, ordering rule, filter or
   tenant scope, transaction owner, and authoritative reader. Inspect the real
   engine and schema; SQLite, a repository mock, and production PostgreSQL are
   different evidence layers.
3. **Write the invariants before a fix.** State which shapes are accepted, what
   an empty input means, how identical and conflicting duplicates behave, which
   writes commit together, and what a partial failure or ambiguous commit means.
   For ordered reads, name the complete stable sort key and cursor boundary. Do
   not guess whether the contract wants whole-batch rollback, row-level
   quarantine, last-write-wins, or conflict rejection; obtain that policy from
   the owner or existing contract.
4. **Reproduce on isolated data.** Run the exact existing focused command with
   the preserved input against the closest safe store. Use a disposable local
   database or transaction that is proved to be isolated before writing. Add
   one positive control that should still work and one negative control that
   would fail under the suspected bug. Query by stable identity after a timeout
   or uncertain write before considering a retry.
5. **Choose one discriminating observation.** Compare the value at the boundary,
   immediately before commit, in the authoritative store, and through the same
   reader the caller uses. If the stored value is correct but the read result is
   wrong, check ordering, filters, joins, pagination, and stale replicas before
   changing the writer. If the stored value is partial after an exception,
   inspect the actual transaction boundary before adding retries.
6. **Fix the owning boundary.** Validate external structure once where it
   enters; keep domain rules with their owner and persistence constraints in the
   store. Use bound parameters and explicit transactions. Implement replay
   behavior at the durable identity boundary; a generated request ID alone is
   not duplicate protection. For keyset pagination, order by a stable tuple
   such as `(created_at, id)` and resume after the last row returned, not a
   lookahead row that was not returned.
7. **Check the affected lifecycle.** Re-run the original failure, then cover the
   applicable representative, empty, malformed, identical-duplicate,
   conflicting-duplicate, mid-batch failure, retry-after-uncertain-commit, and
   ordering/tie cases. For schema or data migration work, also inspect old/new
   reader and writer compatibility, backfill completeness, counts, indexes,
   rollback limits, and startup migration behavior. Do not mutate a
   production-like store or claim a reversible data rollback without explicit
   authorization and a tested recovery path.
8. **Bound the conclusion.** Report the tested input, store, schema, transaction
   result, command, and observed rows. Separate a Python unit test, local
   disposable database, integration database, CI, and deployed store. A local
   fixture establishes only its stated contract; it does not establish
   production contents, engine behavior, migration safety, or agent efficacy.

## Worked task: a page cursor skips the lookahead row

The practitioner case in the local Jobmark example observed five ordered
records traversed with page size two as `[A, B]` then `[D, E]`; `C` was popped as
the lookahead but incorrectly used as the next cursor. The owner was the domain
pagination function. The correction used the last returned record as the
bookmark, and later work added deterministic ordering for timestamp ties. See
the cited [test-only revision](https://github.com/Astatide1337/Jobmark/commit/b3be144cdbb5fd34cc419ce0c119bcb04d24f800),
[focused correction](https://github.com/Astatide1337/Jobmark/commit/d037f6a020d80ba9452e9cc0519467535d91c7b0),
[tie-ordering revision](https://github.com/Astatide1337/Jobmark/commit/885e5d8bd24cf4627b0aea1155a4543698969b1d),
and its [before-fix](https://github.com/Astatide1337/Jobmark/actions/runs/34673673384)
and [after-fix](https://github.com/Astatide1337/Jobmark/actions/runs/34673777530)
CI runs. Those historical checks are practitioner evidence for that Jobmark
change, not evidence about a new repository or database.

Run the bounded local contract with the standard-library SQLite engine:

```bash
uv run --frozen python -m unittest \
  evals.tests.test_python_data_lifecycle -v
```

The positive control traverses every in-scope record exactly once for page
sizes 1, 2, and 3, including a timestamp tie, while excluding another contact
and another tenant. The negative control deliberately resumes from the
unreturned lookahead and reproduces the missing `C`. Empty scope returns no
cursor; a non-positive page size is rejected. This proves the local ordering,
scope, and cursor contract only. On a real task, run the same checks through the
repository's owning query and database test path, preserving its actual
transaction and schema behavior.
