# Safe evolution

This local reference combines pstack's Make Operations Idempotent, Migrate
Callers Then Delete Legacy APIs, and Separate Before Serializing Shared State.
It is the architectural complement to the repository's production and
security skills.

## Trigger

Use when work crosses an external or durable boundary, may be retried or
restarted, changes a shared API, has multiple writers, or resembles a
production migration or release.

## Decision rule

Make the operation converge to one intended state after retries, crashes, and
partial completion. Identify the authoritative owner and rollback before
mutation. Separate independent writers before adding locks or coordination.
When an internal API can be changed atomically and has no external consumers,
migrate callers and remove the legacy path instead of creating permanent dual
behavior.

## Procedure

1. Map the state, consumers, writers, identity, and exact effect boundary.
2. Ask what happens if the operation runs twice or crashes after each step.
3. Use stable identity, content comparison, reconciliation, or an idempotency
   key where the existing owner supports it. Reject conflicting replays.
4. For a coordinated internal refactor, inventory callers, migrate them,
   update behavior tests, and delete the old path in the same wave when safe.
5. Give independent workers separate state. Serialize only when one shared
   writer is a real invariant.
6. Establish rollback and verify the resulting state before publication or
   declaring recovery.

## Principal-engineer lens

The important decision is how the system behaves under uncertainty. A principal
engineer designs for retries, ownership, and evolution before the incident or
the migration makes those choices expensive.

## Evidence

Show the state transition for a successful run, an interrupted run, and a
replay. Verify the same object or end state, not merely a successful command
count. For sensitive or production-like changes, use the full security and
production-safety boundary maps required by those skills.

## Example

An external issue creation that times out should inspect the existing object and
replay the same idempotency key and payload. It should not create a second issue
or treat a draft as a published issue.

## Limit

Do not add an idempotency store, lock, migration framework, or rollback plan to
a read-only local calculation. Match the mechanism to the actual consequence.
