---
name: self-reflect
description: Proactively reassess stuck, prolonged, or settling work and choose the next justified move.
---

# Self-reflect

Use this as a bounded modifier when the work itself signals that direction,
evidence, or effort needs a reset. Invoke it without waiting for the user when
one of these triggers is present:

- **Close:** a task or thread is settling and a final handoff is about to be
  made.
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

If the state is unclear, say what observation would distinguish `progressing`
from `stalled` or `blocked` and obtain that observation before changing course.
If the needed mutation is explicitly outside the current authority and no
remaining observation could change that conclusion, classify the task as
`blocked`, not merely `stalled`; hand back the exact authority or capability
blocker instead of proposing a future implementation sequence.

## Make the mode-specific decision

**Close.** Compare the requested result with the actual artifact and checks.
State the narrowest supported outcome and one lesson only if it changes a
future decision. Classify a proposed durable lesson as `adopt`, `defer`, or
`discard`:

- adopt only a demonstrated, recurring rule or a real safety boundary;
- defer a plausible improvement that lacks a second signal;
- discard an anecdote, preference, or lesson contradicted by the evidence.

Do not edit a skill, global instruction, or workflow merely because one session
was awkward. A durable edit needs the relevant skill-creator procedure and the
user's approval when it changes future behavior.

**Recover.** State the current hypothesis or failed premise, the evidence that
changed its status, and one next check or replan. Continue when that move is
within authority and the acceptance target remains clear. Ask one focused
question when a product choice or missing authority is the blocker. Do not
silently widen scope or turn a recovery reflection into unrelated cleanup.

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
