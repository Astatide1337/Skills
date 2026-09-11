# Design / plan / prototype

## When

Use for a non-trivial architecture decision, implementation plan, or an
explicitly authorized isolated prototype. A small known edit does not need a
ceremonial design route.

## Inputs to establish

- user outcome, acceptance, non-goals, compatibility and source/environment
  constraints;
- current callers, state owners, interfaces, persistence and side-effect
  boundaries;
- whether this is plan-only, a disposable prototype, or an implementation;
- the evidence needed to choose and the authority to run an experiment.

Read [`architect`](../../architect/SKILL.md), [`how`](../../how/SKILL.md), and
[`why`](../../why/SKILL.md) when ownership or historical rationale matters.
Use [`security-and-hardening`](../../security-and-hardening/SKILL.md) or
[`production-safety`](../../production-safety/SKILL.md) for their boundaries.

## Steps and decision points

1. Write a realistic caller/user sequence before naming modules or types.
2. Compare two structurally distinct viable shapes on ownership, data flow,
   invariants, failure/retry, migration, complexity, and security. Do not
   invent alternatives for a trivial choice.
3. Resolve the riskiest material uncertainty with source evidence or the
   smallest authorized disposable experiment. A plan-only request stops here.
4. Choose the simplest shape, name interfaces/state transitions, failure
   behavior, rollback where effects require it, and the first implementation
   step. Keep prototype shortcuts visibly non-production.

## Failure and recovery

If ownership or a contract remains unknown, mark it and ask one focused
question only when the decision cannot be discovered safely. If a prototype
invalidates its premise, report the result and revise the design; do not turn
an experiment into an unrequested permanent framework.

## Completion evidence

Deliver a decision with caller flow, chosen/rejected alternatives, source
evidence, relevant failure/recovery paths, unresolved decisions, and a
verifiable next step. A diagram or compile check alone is not evidence that the
design fits the actual system.

## Example

For a queue consumer, compare claim/ack ownership in the worker versus the
database, trace one success and retry failure, then choose the existing
transaction boundary and record the retry owner.

## Near-miss

“Critique this pasted API shape; do not implement it” returns a bounded design
review and does not rewrite the repository or create an architecture document.
