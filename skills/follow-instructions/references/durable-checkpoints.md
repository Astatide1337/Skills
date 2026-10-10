# Durable task checkpoints

Use before an expected interruption or when a long-running task must survive
session/context loss. Keep a private state file outside the application checkout
where practical. This is an author-maintained continuation record, not evidence
that an outcome occurred and not an automatic agent scheduler.

The input JSON has exactly `objective`, `requirements`, `decisions`,
`next_action`, `blockers`. Requirements have unique `id`, `description`, and
`status`: `pending`, `reported-complete`, or `blocked`. Preserve the user's
literal acceptance; record material accepted decisions and unfinished gates.

```sh
python scripts/checkpoint.py save --workspace /path/to/app --input /private/task.json --state /private/task-state.json
python scripts/checkpoint.py resume --workspace /path/to/app --state /private/task-state.json
python scripts/checkpoint.py save --workspace /path/to/app --input /private/updated-task.json --state /private/task-state.json --expect SHA256_FROM_RESUME
```

Saving uses a private, atomic, fsynced record and exclusive writer lock. Updates
require the current digest, preserve the objective, requirements and decisions,
and increment the sequence. A changed objective explicitly starts a separate
checkpoint; do not silently erase the old task. The supplied workspace identity
must match on resume. Secrets never belong in this record.

For [approved delivery](approved-plans.md), use these existing fields without a
new schema: retain the original acceptance and requirement IDs in `objective`
and `requirements`; append plan/prototype version, paths/digests, exact user
confirmation, permitted effects and superseding approvals to `decisions`.
Record failed approaches, source delta and remaining-check/evidence links in
`decisions`, the next bounded action in `next_action`, and exact unavailable
gates in `blockers`. Author state does not itself establish approval provenance
or independent verification; preserve the actual confirmation/evidence source.

When accepted requirements change, start a new linked checkpoint and retain
the old one. Do not rewrite immutable requirement descriptions or silently
remove acceptance. Ordinary status updates and in-contract decisions use the
existing digest-checked update path.

Resume reconstructs the objective and next action. Recheck current source,
capabilities and acceptance evidence before acting; `reported-complete` does not
mean verified, and a checkpoint does not establish source/runtime freshness.
Keep any pending independent-review or publication gate. Run an actual
interruption/resume case before claiming this prevents context loss; a simulated
handoff only checks the handoff's declared contents.
