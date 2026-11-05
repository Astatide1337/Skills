# Delivery history

Use during substantial authorized implementation to retain evidence of what
needed correction and what happened after delivery. Reuse the repository's
existing task and PR records. They own status, requirements and acceptance;
this history is a rebuildable index, never another authority or completion gate.
Read-only work may inspect the index without creating or updating it.

## Enroll and maintain

The integrating parent owns one current JSON snapshot per task under the
existing private wiki's `outcomes/` directory. Apply the [wiki exclusion and
privacy rules](codebase-knowledge.md#discover-then-build-only-what-is-missing)
before writing; do not commit the index, embed transcripts or copy secret-bearing
logs. Use an equivalent existing private location when the repository has one.
Workers return evidence to the parent, not concurrent edits to the same record.

Enroll at the start of substantial work, with a stable task ID and sources for
the request and current task state. Resume the same ID after interruptions;
multiple PRs or retries of one task do not become independent successes.
Refresh the snapshot from authoritative sources at handoff, interruption and
when later feedback arrives. Replace the snapshot rather than appending a
second version. Rebuild stale or inconsistent records from their sources;
never alter source evidence to match a summary. Unknown or disputed information
stays visible. Record an abandoned or interrupted task instead of dropping it.
A cancellation ends work immediately; indexing does not authorize extra work.

Do not invent a start time for retrospective records. If actual enrollment was
missed, note the gap in the pilot's task record rather than claiming prospective
coverage. An unavailable index does not stop implementation or acceptance;
retain source evidence and repair the index when access is available.

## Describe observations, then assess them

For each useful observation, state a claim, source locations and one assessment:
`defect`, `not-defect` or `undetermined`. These are attributed judgments in the
index, not conclusions established by the helper. Preserve the review or user
statement that supports the assessment; disagreement remains `undetermined`
until the source record resolves it. Do not call the parent's own classification
independent review.

| Category | What to distinguish |
| --- | --- |
| `user-correction` | A misunderstood requirement versus a newly requested change |
| `completion-prompt` | A user had to request already-authorized unfinished work |
| `review-caught` | A real defect caught before delivery; useful review, not an escaped bug |
| `escaped-defect` | A demonstrated defect discovered after the claimed delivery |
| `reopened` | Incorrect prior acceptance versus new requirements or evidence |
| `unsupported-claim` | A specific claim whose required support is absent or contradicts it |
| `coordination-waste` | Observed duplicate or unnecessary work, with its concrete cause |
| `scope-change` | An accepted change in requirements; link the decision, not an inferred failure |

No observation is required merely to fill a category. Missing follow-up stays
`unknown`; silence is not evidence of successful use. `observed` means an actual
follow-up was examined at the recorded time, not that it found no bugs forever.
A negative observation must name what was checked and the period covered in its
source. Reuse supported watches or later authorized work; do not install a
scheduler or silently start indefinite monitoring.

## Snapshot and helper

Each `.json` file contains exactly these fields:

- `schema_version`: `1`; `repository`, `task_id`, `task_type`: nonempty strings.
  Choose a consistent task type from actual work, such as `bug-fix`, `ui-change`,
  `review` or `deployment`; do not change it to improve a summary.
- `started_at`, `recorded_at`: timezone-aware ISO timestamps, in that order.
- `status`: `active`, `delivered`, `interrupted` or `abandoned`. `delivered`
  reflects the task's authorized stopping point, not necessarily merge or deploy.
- `sources`: objects with `role` and `locator`. A locator is an HTTPS URL without
  credentials or an absolute local evidence path. Use immutable revisions or
  retained observations with source/build identity where the claim needs them.
  Always include `request` and `state`; `delivered` also needs `delivery` and
  `acceptance`. A link's existence or shape does not prove its content.
- `observations`: objects with `id`, `category`, `assessment`, `claim`, `sources`.
  IDs are unique within the task. Sources use the same shape; valid roles are
  `request`, `state`, `delivery`, `acceptance`, `claim`, `trace`, `detection`,
  `prior-delivery`, `decision`, `review`. Each observation needs a source.
  `unsupported-claim` requires `claim` and `trace`; `escaped-defect` requires
  `detection` and `prior-delivery`; `scope-change` requires `decision`;
  `review-caught` requires `review`. The trace must support the missing-check
  assessment; an incomplete trace is insufficient to establish nonexecution.
- `followup`: `state`, `as_of`, `sources`. For `unknown`, use `null` and `[]`.
  For `observed`, provide a timestamp between enrollment and the snapshot and
  nonempty sources. An empty observation list is valid in either state.

Use the bundled [read-only helper](../scripts/delivery-history.py):

```sh
python3 skills/follow-instructions/scripts/delivery-history.py validate /absolute/private/wiki/outcomes
python3 skills/follow-instructions/scripts/delivery-history.py summary /absolute/private/wiki/outcomes
```

It checks structure and duplicate task/observation identities, then reports task
counts separately from observation counts, grouped by repository and task type.
It does not read linked evidence, verify independence, judge correctness, change
records, accept work or publish anything. Malformed input fails rather than
silently removing unfavorable records from the summary. Valid records can still
contain false judgments; inspect their sources before relying on a conclusion.

## Pilot and feedback

Before a pilot, define its repositories, task types and enrollment window in the
existing task record. Enroll all eligible tasks, including interrupted attempts.
Use the actual issue/thread/task list to construct an independent inventory of
`repository` and `task_id` pairs. Keep it outside `outcomes/` and pass its path
with `--inventory` to either helper command. Missing and unexpected identities
must be reconciled against the sources before describing coverage as consecutive.
Matching the inventory checks identities only; it cannot prove that the inventory
itself is complete. Without an inventory, coverage is explicitly unverified.

Inspect intervention, review catches, escapes, unsupported claims and reopens
separately. Do not add them into a failure total: one defect may produce several
observations. Compare only like task types and retain unknown follow-up. Keep
actual model, reasoning and usage receipts in source records when available;
missing usage stays unknown. The helper does not estimate costs or produce rates,
confidence scores or an automatic grant of additional authority.

Use [failure recovery](../../self-reflect/references/learn-from-repeats.md) to
repair a demonstrated cause at its owner. A useful regression catches the
original defect and accepts a valid alternative. A historical record or a passing
helper test does not show that a guidance change improved agents; use the
existing [comparison procedure](../../skill-creator/references/evaluation.md)
for that claim. Keep routine handoffs concise; surface the history only when it
changes a decision or the user asks to inspect it.
