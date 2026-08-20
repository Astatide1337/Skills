# Code archaeology

Start from the exact symbol, line, constant, or boundary in question.

1. Read enough surrounding code to understand the current mechanism.
2. Use line history to find the introducing or materially changing commit.
3. Inspect the complete commit, including tests, adjacent files, and message.
4. Follow renames and moves. Search distinctive strings, old symbol names, and
   related configuration rather than assuming the current path is stable.
5. Search parent and child commits when the change was split, reverted, or
   repaired shortly afterward.
6. Search referenced issue or PR identifiers and release notes when available.
7. Compare historical constraints with current configuration and runtime
   evidence before recommending removal.

Useful evidence includes tests added with the change, comments later deleted,
nearby constants, failure-handling code, configuration defaults, and commits
that revert or narrow the behavior. None proves intent alone. Preserve dates,
authors, identifiers, and exact paths so another investigator can reproduce the
lineage.

Record unsuccessful searches when they rule out an obvious source. Stop when
the remaining sources are unavailable or further search is unlikely to change
the confidence tier, then state that limitation.
