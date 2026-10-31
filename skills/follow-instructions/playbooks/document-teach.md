# Document / teach

## When

Use when the requested deliverable is an explanation, source-linked document,
or teaching handoff. Distinguish chat explanation from writing or publishing a
file. Use [`how`](../../how/SKILL.md), [`why`](../../why/SKILL.md), or
[`teach`](../../teach/SKILL.md) for their specific source/history/learning
methods, and [`unslop`](../../unslop/SKILL.md) only for an explicit rewrite.

## Inputs to establish

- audience, format, destination, source/revision, and whether publication or
  file mutation is requested;
- concepts the reader needs, actual data flow/ownership/invariants, and
  examples/commands that can be checked;
- factual uncertainty, visual/runtime evidence requirements, and non-goals.

## Steps and decision points

1. Inspect the authoritative implementation and relevant callers/state before
   explaining. Separate source facts, inference, and open questions.
2. Structure the explanation for the reader's task. Check executable recipes
   against their actual bindings and effects, not just comments or syntax.
   For state-changing instructions, inspect relevant writers and readers of
   that state: establish preconditions, expected effects, and states that must
   remain denied. Use source or an authorized isolated run; distinguish those
   proof layers. For UI or motion claims, inspect the rendered state.
3. Deliver in the requested channel. Add a teach-back prompt only when it
   materially helps learning; do not turn every explanation into homework.

## Failure and recovery

If source, runtime, or visual evidence is missing, label the limit and do not
fill it with an invented architecture. Keep execution QA separate from the
reader's learning. Do not edit README/docs merely because explanation would be
convenient unless the user requested that artifact.

## Completion evidence

Return the requested artifact with checked source links/examples and explicit
unknowns. A generated diagram or polished prose is not proof of the behavior
it depicts.

## Example

A maintenance guide reverses a disable operation by setting `enabled: true`.
But the same state also represents quarantine, with the reason recorded in
another field. A valid update can silently undo that policy. Inspect the other
writers and the consumer before recommending the inverse: routine disablement
may be reversed after its preconditions are met; quarantine needs its own
review. A wording-only edit can reuse unchanged, covering evidence.

## Near-miss

“What does this pasted expression do?” answers from the supplied text only;
it does not invoke repository teaching or write documentation.
