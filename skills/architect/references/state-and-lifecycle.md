# State and lifecycle boundaries

Use when a change affects asynchronous saves, cancellation, conflicting edits,
retries, shared views, or owned resources. Identify who owns each state, which
transitions are allowed, when a change
commits, and what success and failure produce.

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
6. Clean up only resources you can identify as created by this run. Record
   failed cleanup as unfinished work and retain the verification evidence.
7. When a state, guard or quota controls release, deletion or a new launch,
   treat uncertainty as a state. Save a resource's ID as soon as it exists, before a
   later step can fail.
   If migrated records lack IDs, investigate whether creation completed before
   marking them resolved. A confirmed missing resource resolves only that ID;
   an empty lookup of known IDs says nothing about resources with unknown IDs
   or requests that partially failed.
   Apply the same actor-scoped guard at producers and consumers, including
   already-queued work and pre-upgrade records, while keeping authorized cleanup
   possible.

Test normal completion, rejection/conflict, interruption before commit, and
interruption after commit wherever those states exist. Choose expected effects
before running: persisted values, retained input, navigation, resource state,
and returned status. Run the real application's path when claiming integration;
controlled callback fixtures test only the transitions they exercise.

These decisions respond to discarded drafts, duplicate retries, and divergent
views in the original private audit summaries, plus the user-reported
cancellation scenario; item 7 responds to the cleanup and quota repair rounds in
Skills issue 40. Machine attribution remains unestablished. This reference
does not claim the original applications were repaired.
