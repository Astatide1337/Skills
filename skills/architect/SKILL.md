---
name: architect
description: When implementation boundaries or ownership need design.
---

# Architect

Design from the caller inward, then implement against the chosen shape.
Modularity means an ordinary change, addition or removal has a clear owner and
does not force unrelated changes. Create an interface to hide a demonstrated
decision or invariant, not to prepare a framework for imagined features.

For a design-only deliverable, make the contract executable in the reader's
head. Include: realistic caller usage; public types or signatures; module
ownership; success and failure sequences; transaction, durability, or side-
effect boundaries; retry ownership; and unresolved decisions. Do not hide a
missing ownership decision behind a diagram or generic interface name.

1. Ground the existing system with `how`; use `why` when historical rationale constrains the change.
2. Write realistic caller usage before types. When choosing a boundary, data
   shape or shared state, apply [construction decisions](../follow-instructions/references/principles/ownership-and-domain.md#construction-decisions-and-counterexamples).
3. Produce at least two structurally distinct candidate designs. Do this locally, or with collaborators only when permitted.
4. Compare candidates on interface depth, ownership, data access, boundary validation, invariants, state transitions, failure recovery, and likely evolution.
5. Reject shallow modules, information leakage, temporal decomposition, pass-through layers, and speculative generality.
6. Record the chosen shape, accepted tradeoffs, rejected alternative, risks,
   unresolved decisions, purposeful refactors and first implementation step.
7. Implement against the sketch. Treat repeated deviations as evidence the architecture is wrong; re-ground and redesign instead of adding escape hatches.

Before handing off a design-only result, trace one successful operation and one
failure through the proposed signatures. For asynchronous or durable delivery,
show how work is claimed, acknowledged, failed, and retried, and state which
transaction can commit independently. Correct any signature that cannot support
the written sequence.

For nontrivial feature/issue delivery, use the coordinator's
[approved-plan contract](../follow-instructions/references/approved-plans.md).
Material contract, ownership, architecture or migration changes reopen that
plan; in-contract simplification can proceed within the existing approval.
Standalone design and the tiny-change path retain their requested boundaries.

Use `references/rationale-template.md` for the decision record. Read
`references/design-red-flags.md` when comparing module boundaries or reviewing
an existing proposal.
For asynchronous saves, conflicts, retries, shared views, or owned resources,
read [state and lifecycle boundaries](references/state-and-lifecycle.md).
