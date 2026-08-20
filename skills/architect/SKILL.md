---
name: architect
description: Sketch types, signatures, usage, data flow, and module boundaries before implementing non-trivial work. Use when jumping directly to code risks locking in the wrong ownership or public interface.
---

# Architect

Design from the caller inward, then implement against the chosen shape.

For a design-only deliverable, make the contract executable in the reader's
head. Include: realistic caller usage; public types or signatures; module
ownership; success and failure sequences; transaction, durability, or side-
effect boundaries; retry ownership; and unresolved decisions. Do not hide a
missing ownership decision behind a diagram or generic interface name.

1. Ground the existing system with `how`; use `why` when historical rationale constrains the change.
2. Write realistic caller usage before types.
3. Produce at least two structurally distinct candidate designs. Do this locally, or with collaborators only when permitted.
4. Compare candidates on interface depth, ownership, data access, boundary validation, invariants, state transitions, failure recovery, and likely evolution.
5. Reject shallow modules, information leakage, temporal decomposition, pass-through layers, and speculative generality.
6. Record the chosen shape, accepted tradeoffs, rejected alternative, risks,
   unresolved decisions, and first implementation step.
7. Implement against the sketch. Treat repeated deviations as evidence the architecture is wrong; re-ground and redesign instead of adding escape hatches.

Before handing off a design-only result, trace one successful operation and one
failure through the proposed signatures. For asynchronous or durable delivery,
show how work is claimed, acknowledged, failed, and retried, and state which
transaction can commit independently. Correct any signature that cannot support
the written sequence.

Pause for approval only when requested or when the choice changes public contracts, data ownership, migration strategy, or other material scope.

See `references/rationale-template.md`.
