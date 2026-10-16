# Design / plan / prototype

## When

Use for a non-trivial architecture decision, implementation plan, or an
explicitly authorized isolated prototype. A small known edit does not need a
ceremonial design route.
For feature/issue delivery, apply the
[approved-plan contract](../references/approved-plans.md); it owns plan contents,
approval identity and materiality rather than duplicating those rules here.

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

1. Inspect the actual owners, conventions, callers, tests and environment, then
   write a realistic caller/user sequence before naming modules or types.
   For a substantial product feature, identify the intended user, their main
   action, and its observable result from the supplied requirements. Preserve
   the interaction that makes that result useful when splitting work into
   components; component completion alone is not the product acceptance.
2. Compare credible alternatives when a real choice remains, using the relevant
   ownership, data flow, failure/retry, migration, complexity, and security
   constraints. Do not invent alternatives for an established correction.
3. Resolve the riskiest material uncertainty with source evidence or the
   smallest authorized disposable experiment. A plan-only request permits only
   its observation and explicitly authorized prototype effects, not dependent
   implementation; still choose and explain the recommendation.
   When usefulness depends on an interaction, choose a representative complete
   path for early proof, including its actual input and resulting effect.
4. Choose the simplest shape, name interfaces/state transitions, failure
   behavior, rollback where effects require it, and the first implementation
   step, including purposeful refactors. For nontrivial feature/issue delivery,
   record the plan in the existing task record. Prepare a relevant actual-component
   prototype when it resolves a design uncertainty. Present a separate approval
   artifact and await confirmation only when the user or project requires it.
   Standalone design uses the requested deliverable. Label prototype shortcuts.

## Failure and recovery

If ownership or a contract remains unknown, mark it and ask one focused
question only when the decision cannot be discovered safely. If a prototype
invalidates its premise, report the result and revise the design; do not turn
an experiment into an unrequested permanent framework.

## Completion evidence

Deliver a decision with caller flow, chosen/rejected alternatives, source
evidence, relevant failure/recovery paths, unresolved decisions, and a
verifiable next step. A diagram or compile check alone is not evidence that the
design fits the actual system. Record the plan/prototype identity, confirmation
when received and unresolved gates; lack of confirmation means implementation
is pending, not that investigation or the plan itself is unfinished.

## Example

For a queue consumer, compare claim/ack ownership in the worker versus the
database, trace one success and retry failure, then choose the existing
transaction boundary and record the retry owner.

## Near-miss

“Critique this pasted API shape; do not implement it” returns a bounded design
review and does not rewrite the repository or create an architecture document.
