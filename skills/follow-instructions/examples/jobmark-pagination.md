# Worked example: Jobmark interaction pagination

This is a source-grounded example of `investigate causes and test behavior`,
`establish state and ownership first`, and `verify the real behavior`. It is
not evidence that every workflow or model is correct.

## Problem and owner

Jobmark's MCP `interactions_list` handler calls `listInteractions`, which asks
PostgreSQL for an ordered page and returns a continuation cursor. The original
implementation removed the first record it had not returned and used that
record's ID as the next cursor. PostgreSQL then skipped that record on the
following request.

With five records and a page size of two, the observed traversal was:

```text
before: [A, B] -> [D, E]       C is missing
after:  [A, B] -> [C, D] -> [E]
```

The owner is the domain pagination function, not a second cursor algorithm in
the MCP transport. The requested behavior also preserves user/contact filters
and tenant isolation.

## Evidence and correction

The original test-only revision was
[`b3be144c`](https://github.com/Astatide1337/Jobmark/commit/b3be144cdbb5fd34cc419ce0c119bcb04d24f800).
The focused correction was
[`d037f6a`](https://github.com/Astatide1337/Jobmark/commit/d037f6a020d80ba9452e9cc0519467535d91c7b0).
The later published head added deterministic ordering for timestamp ties at
[`885e5d8`](https://github.com/Astatide1337/Jobmark/commit/885e5d8bd24cf4627b0aea1155a4543698969b1d).

The minimal production change bookmarks the last record already returned:

```diff
- const next = interactions.pop();
- nextCursor = next!.id;
+ interactions.pop();
+ nextCursor = interactions[interactions.length - 1].id;
```

The regression file was left unchanged between the failing and passing runs.
The [before-fix CI run](https://github.com/Astatide1337/Jobmark/actions/runs/34673673384)
failed on skipped records and the MCP handler cursor. The
[after-fix CI run](https://github.com/Astatide1337/Jobmark/actions/runs/34673777530)
passed the published test suite. Those historical runs prove the original
correction, not the later tie-ordering commit and not this Skills package.

The separate [Jobmark PR #48](https://github.com/Astatide1337/Jobmark/pull/48)
is now merged at the later head. It remains separate from the Skills review
unit. Do not relabel its historical CI as a new replay.

## What to check on a new task

1. Read the handler, domain function, query ordering, and cursor contract.
2. Run the unchanged regression against the pre-change checkout when the
   environment permits.
3. Apply the smallest owner-level correction.
4. Traverse the real local PostgreSQL path at several page sizes, including the
   final page, filters, tenant separation, and timestamp ties.
5. Inspect the final diff and report whether the evidence is unit,
   integration, browser, or live-service evidence.

The Skills v1 replay is deliberately local and disposable. Its result is
recorded only after a native agent uses the installed entry skill against the
test-only checkout. A missing local database or browser capability is a
blocker, not permission to substitute a fake tracker, canned answer, or source
fragment.
