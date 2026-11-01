# State and lifecycle boundaries

Use when a change affects asynchronous saves, cancellation, conflicting edits,
retries, shared views, or owned resources. Finish with one explicit state owner,
legal transitions, the commit boundary, and observed success/failure effects.

1. Trace the actual caller and name the authoritative state, writer, pending
   work, and irreversible effect. A hidden dialog is not cancelled work.
2. State what can be cancelled before commit and what must be reported after
   commit. Check the signal at the last safe boundary; settle pending work and
   inspect persistence/navigation. A committed save remains saved.
3. Preserve a user's draft separately from the server revision. A stale-write
   rejection retains the draft; reconciliation precedes a bounded retry.
4. Observe a write with an uncertain result by stable identity before retrying.
   Idempotency belongs at the owning boundary; duplicate-prevention claims need
   an actual retry/concurrency check, not merely a generated request ID.
5. Derive multiple views from the same authoritative state. Exercise a state
   transition through every clearly affected view rather than checking labels.
6. Clean up only resources with inspectable run ownership. Failed cleanup is
   retained as unfinished work; it does not erase verification evidence.
7. When a state, guard or quota controls release, deletion or a new launch,
   treat uncertainty as a state. Persist an identity as soon as it exists,
   before a later step can fail. Keep a record migrated without identity
   unresolved, and release only on positive evidence for every resource that may
   exist: an empty lookup is not that evidence. Scope a new guard to the owning
   actor so it also covers already-queued work and pre-upgrade records, and keep
   the cleanup path open.

Test normal completion, rejection/conflict, interruption before commit, and
interruption after commit wherever those states exist. Choose expected effects
before running: persisted values, retained input, navigation, resource state,
and returned status. Run the real application's path when claiming integration;
controlled callback fixtures prove only their bounded transition contract.

These decisions respond to discarded drafts, duplicate retries, and divergent
views in the original private audit summaries, plus the user-reported
cancellation scenario; item 7 responds to the cleanup and quota repair rounds in
Skills issue 40. Machine attribution remains unestablished. This reference
does not claim the original applications were repaired.
