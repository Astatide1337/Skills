# Durable task checkpoints

Use before an expected interruption or when a long-running task must survive
session/context loss. Keep a private state file outside the application checkout
where practical. The record helps the next session continue. Its status fields do not prove
completion, and saving it does not schedule another run.

Prefer the attached runtime's native conversation/checkpoint and resume
facilities. For T3 children, retain task identity and use the documented task
controls, completion wakes and cancellation. New independent reviews use new
tasks, not thread-send. Use thread reads for context when needed; creating a
top-level thread or interrupting a child's underlying thread does not replace
the supported task controls. A saved conversation is not automatic scheduling,
and stopping a task may require an explicit supported resume. Do not create
another ledger/database.

Before a real interruption retain the objective, acceptance, constraints/authority,
branch and PR/MR, current result, unresolved checks and findings, failed
approaches and next useful action in the existing task record. On resume, compare
that record with live source and host state. Reported completion is not evidence.
For delegated work, also record the requested and actual provider, model and
reasoning level, each worker's assignment, returned result and revision, task ID,
pending findings and dependencies. Do not copy transcripts or create another queue.
Use the helper below only when native persistence cannot retain that record or a
portable file handoff is needed. Tiny edits need neither mechanism.

The input JSON has exactly `objective`, `requirements`, `decisions`,
`next_action`, `blockers`. Requirements have unique `id`, `description`, and
`status`: `pending`, `reported-complete`, or `blocked`. Preserve the user's
literal acceptance; record material accepted decisions and unfinished gates.

Run these commands from the installed `follow-instructions` skill directory.
Use its supplied path to locate `scripts/checkpoint.py`. Choose existing
workspace and private state directories. Replace `SHA256_FROM_RESUME` with the
`sha256` string from the resume command's JSON output.

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

For [authorized
delivery](../../pull-requests/SKILL.md#complete-authorized-delivery), use these
existing fields without a new schema: retain the original acceptance and
requirement IDs in `objective` and `requirements`; append plan/prototype
version, paths/digests, exact user confirmation, permitted effects and
superseding approvals to `decisions`. Record failed approaches, changes since
the previous checkpoint (including uncommitted work), and links to remaining
checks and evidence in `decisions`, the next bounded action in `next_action`,
and exact unavailable gates in `blockers`. A status written by the agent does
not prove approval or independent verification; preserve the actual
confirmation/evidence source.

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
