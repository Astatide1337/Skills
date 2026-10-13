# Durable task checkpoints

Use before an expected interruption or when long-running work must survive
context loss. Prefer the harness's existing task state. The optional helper
below supports a private file when native continuation is insufficient; it is
not a prerequisite for ordinary work or an automatic scheduler.

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

For [planned work](approved-plans.md), retain acceptance, relevant user decisions
and permitted effects, changed source, failed approaches, and remaining checks.
Store the next action and actual blockers. Plan versions or approval digests are
needed only when explicitly requested. Author state is not independent
verification; retain the evidence source.

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
