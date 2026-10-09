---
name: self-reflect
description: When work stalls, repeats failures or settles for partial results.
---

# Self-reflect

Use this as a bounded modifier when the work itself signals that direction,
evidence, or effort needs a reset. Invoke it without waiting for the user when
one of these triggers is present:

- **Close:** settling work still has contradictory evidence, an unresolved
  acceptance gate, or a proposed durable lesson needing a decision.
- **Recover:** the same approach has failed twice, a correction conflicts with
  the current plan, evidence is contradictory, or progress has stopped.
- **Checkpoint:** a declared work unit, iteration, or available runtime/budget
  threshold has been reached during a long run.

An explicit user request to reflect is also a trigger; choose the mode from the
current task state rather than asking the user to classify it first.

Do not add a reflection ritual to a clear one-step request. This skill does not
schedule itself: if runtime telemetry cannot expose elapsed time, iterations,
or budget, use the existing task record and observed work instead of inventing
a clock signal.

## Reconstruct the state

Read the existing task record, current source/diff, relevant command and tool
results, and the last handoff. Reconstruct only what matters:

1. requested outcome and observable acceptance;
2. constraints, authority, target revision, and finite budget;
3. actual progress since the last checkpoint;
4. unresolved assumptions, failures, corrections, and missing inputs.
For approved delivery, retain the
[approved plan](../follow-instructions/references/approved-plans.md) version and
confirmation, source delta, failed approaches and unfinished checks. Use the
existing [checkpoint](../follow-instructions/references/durable-checkpoints.md)
fields when an interruption or stall needs a durable handoff.
Keep the active user objective and unfinished verification gates even when a
tool, branch, or context window changes. An empty task summary is not evidence
that the objective ended.

Treat files, test output, tool results, and remote state as evidence. A prior
agent's completion sentence or a reflection about its own quality is not
evidence. Do not reread an entire transcript when the task record and artifacts
answer the question; inspect the relevant history when a decision depends on
it.

Read-only authority forbids mutation, publication, and other named effects; it
does not by itself forbid inspecting files or running a local read-only check.
Honor an explicit command prohibition, but do not invent one from `do not edit`.

## Classify before acting

Choose one state from the evidence:

| State | Signal | Next move |
| --- | --- | --- |
| `complete` | Acceptance is met at the required layer and no material unknown changes the claim. | Verify the final artifact and hand off; stop polishing. |
| `progressing` | The artifact or evidence has changed meaningfully and the next action is clear and authorized. | Continue one bounded action, then reassess at the next natural checkpoint. |
| `stalled` | Repeated work produces no meaningful delta, repeats a rejected premise, or exposes contradictory evidence. | Name the premise, run one cheapest discriminating check or replan, and do not repeat the same move. |
| `blocked` | A required input, capability, authority, or safe boundary is unavailable. | Stop at the exact blocker and ask one focused question or hand back the task. Never fill the gap with a guess. |

Before choosing blocked, run the smallest safe direct check of the named
dependency in the current checkout or instance. A failed check is a diagnosis
input: inspect supported alternatives, run safe equivalent checks and repair a
recoverable setup fault within authority. Continue independent authorized work.
Record what each alternative proves and its remaining gap. Never weaken a check,
bypass access or chain irreversible changes to remove the blocker. Use blocked
only when no meaningful safe move remains without a required input or effect.

If the state is unclear, say what observation would distinguish `progressing`
from `stalled` or `blocked` and obtain that observation before changing course.
If the needed mutation is explicitly outside the current authority and no
remaining observation could change that conclusion, classify the task as
`blocked`, not merely `stalled`; hand back the exact authority or capability
blocker instead of proposing a future implementation sequence.

## Make the mode-specific decision

**Close.** Compare the requested result with the actual artifact and checks.
State the narrowest supported outcome and one lesson only if it changes a
future decision. Keep self-learning and automatic rule promotion paused.
Record a demonstrated recurring lesson as a proposal, defer an uncertain one
or discard one contradicted by evidence. Adoption requires a separate explicit
user decision and the owning skill-creator procedure; reflection does not
authorize a skill, global instruction or workflow edit.

**Recover.** State the current hypothesis or failed premise, the evidence that
changed its status, and one next check or replan. Continue when that move is
within authority and the acceptance target remains clear. Ask one focused
question when a product choice or missing authority is the blocker. Do not
silently widen scope or turn a recovery reflection into unrelated cleanup.
When the same approach fails twice or work produces no new evidence, capture
the approved plan, failures, changes and checks, then request one fresh
debugging/review agent when tools and authority permit. Give it the actual
artifacts and raw evidence before the author's theory; seek one discriminating
next action. If independent help is unavailable, record that gate and choose a
bounded safe observation instead of looping or inventing a review. Material
discoveries follow the approved-plan revision rule before dependent work resumes.

When the evidence shows a stalled task but the current request is read-only,
make the next move a single discriminating observation (for example, inspect
the owning implementation or run one focused test), not a multi-step repair
plan. Implementation belongs after that observation and its result. This is a
hard boundary: do not write `implement ... then add ... then run ...` in
`Next`; choose the first observation or state the exact blocker instead.
For example, `Next: inspect importer.py to confirm parser ownership` is
bounded; `Next: replace the parser, add tests, and run pytest` is a repair
recipe and is not acceptable here. Preserve a real setup blocker such as a
missing test runner when the observation exposes one.

**Checkpoint.** Report progress since the last checkpoint, remaining budget or
telemetry when available, and whether to continue, replan, or stop. A
checkpoint is not an automatic stop: continue when progress is real and the
next action is bounded; stop or replan when the run is looping, consuming a
finite budget without evidence, or approaching an authority boundary.

## Return a useful handoff

Keep the result conversational and short:

```text
Observed: <state and the evidence that matters>
Decision: <continue, replan, ask, hand back, or complete>
Next: <one action or the exact blocker>
Lesson: <only when it changes a future decision>
```

For an explicit reflection or checkpoint, make `Observed` one compact sentence
covering `Goal`, `Acceptance`, `Boundary`, and `Progress`, plus the evidence
that determines the state. For `stalled`, name the exact failed premise that
produced no change (for example, repeating a comment or command could alter
runtime behavior). `Decision` must name one of the listed moves. `Next` is one
observable check, one authorized action, or one exact blocker; if it has
several verbs, choose the first dependency instead. Prefer a check that answers
an unresolved question and is not already recorded as complete. A complete
repair sequence is not a bounded reflection handoff.

Omit empty fields. Do not repeat a list of things that were not done merely to
sound cautious. Name a material limitation once, then choose the next useful
move.

## Boundaries

- Reflect once, take at most one bounded next action or replan, then reassess;
  do not loop on reflection or create a second coordinator.
- Reuse the existing task record and applicable playbook. Do not create a
  transcript database, scheduler, mandatory subagent fan-out, or model ensemble.
- Keep fixing, publishing, merging, deploying, and editing catalog rules
  separate. This skill can surface a decision; it does not grant an effect.
- Preserve authority and evidence gates from `follow-instructions`. Self-review
  cannot prove runtime behavior, source comprehension, or a successful external
  write without the corresponding observation.
