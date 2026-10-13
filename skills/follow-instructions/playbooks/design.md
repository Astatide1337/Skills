# Design / plan / prototype

## When

Use for a requested design, consequential ownership decision, or authorized prototype. A substantial implementation does not automatically require a separate approval cycle.

## Inputs to establish

- Outcome, acceptance, constraints, current owners/callers, and allowed prototype effects.
- User-owned decisions versus facts discoverable from source or an experiment.

## Steps and decision points

1. Inspect the real system and write the caller/user flow, including a success and relevant failure.
2. Compare alternatives when they expose a genuine tradeoff in ownership, interfaces, data, failure recovery, or complexity.
3. Resolve material uncertainty with evidence or an authorized disposable experiment. Plan-only work stops before dependent implementation.
4. Recommend the simplest viable shape, useful acceptance checks, and first implementation step. Use the requested medium; HTML and clickable prototypes are optional ways to make a decision reviewable.
5. Apply [planning and continuation](../references/approved-plans.md), reusing existing authorization.

## Failure and recovery

Name an unresolved consequential choice and provide a concrete recommendation before asking. If an experiment invalidates a premise, revise the design without making the prototype a permanent framework.

## Completion evidence

Deliver a source-grounded recommendation, meaningful tradeoffs, failure/recovery behavior, and next step. A diagram does not prove runtime behavior.

## Example

Compare queue acknowledgment ownership, trace a success and retry, and select the existing transaction boundary.

## Near-miss

A request to critique a pasted API does not authorize implementation or a permanent design document.
