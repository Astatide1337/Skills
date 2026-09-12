# Issues / draft, create, update, triage

## When

Use for a tracker issue's content or lifecycle. `draft` returns copy only;
`create`/`update`/`triage` have only the explicitly requested tracker effects.
No issue task authorizes code edits, PRs, or deployment by implication.

## Inputs to establish

- exact repository/tracker, mode, current issue/comments, templates and user
  authority;
- problem evidence, expected/observed behavior, source locations, constraints,
  non-goals and duplicate candidates;
- for an update, which old instruction is superseded; for a write, readback and
  ambiguous-failure behavior.

## Steps and decision points

1. Read the current issue and relevant comments for update/triage. Search for
   duplicates before create. Keep facts, hypotheses, and proposed interfaces
   distinct; never copy sensitive data.
2. Write the smallest coherent **Problem**, **Scope**, **Acceptance**, and
   optional **Implementation notes**. Acceptance must be observable, not a
   file-count or vague quality promise.
3. In draft mode, stop before remote writes. In create/update mode, perform
   only the requested write, then fetch the returned object and verify
   repository, title, essential body, status, and superseded scope. In triage,
   return an evidence-backed recommendation without unrequested labels,
   assignment, closure, or implementation.

## Failure and recovery

On a timeout or ambiguous write, search/fetch current state before retrying so
one request cannot create duplicates. If readback is unavailable, report a
partial or unknown publication result; do not claim success from a local copy.
If source evidence is missing, mark it and keep the issue actionable without
inventing a cause.

## Completion evidence

Provide draft text or exact tracker ID/URL, fetched-back essential fields and
status, write/readback observations, and forbidden effects that remained absent.
An issue comment or final response is not itself proof of remote state.

## Example

Investigate a tenant lookup, create exactly one test-tracker issue containing
the source-grounded finding and cross-tenant acceptance case, then fetch it
back; do not edit code or open a PR.

## Near-miss

“Draft an issue for this pasted symptom; do not post it” returns concise copy
and does not search or mutate a remote tracker.
