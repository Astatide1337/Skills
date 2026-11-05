---
name: architect
description: "Use when designing APIs or schemas, changing ownership, or resolving uncertain module boundaries."
---

# Architect

Start with real caller usage. Give each decision and invariant a clear owner so
ordinary changes do not require edits to unrelated modules. Add an interface
when it hides complexity that callers would otherwise need to understand.
Do not add a framework for hypothetical features.

For a design-only task, show realistic calls, public types or signatures, module
ownership, and one success and failure sequence. Identify transaction and
side-effect boundaries, durability, retry ownership, and unresolved decisions.
A diagram cannot replace a missing ownership decision.

1. Inspect the responsible code, its callers and a comparable accepted change.
   Use `how` for an unclear call flow and `why` when history constrains the design.
   Start from established interfaces and operational conventions.
2. Write caller usage before types. For a boundary, data shape or shared-state
   decision, apply [construction
   decisions](../follow-instructions/references/principles/ownership-and-domain.md#construction-decisions-and-counterexamples).
3. Compare alternatives only when a real design choice remains. An established
   correction does not need a competing design.
4. Check ownership, data access, validation, state transitions, recovery and the
   changes the system is likely to need.
5. Reject shallow modules, information leakage, temporal decomposition,
   pass-through layers and speculative generality. Use the linked red flags
   to distinguish these defects from useful boundaries.
6. Record the chosen design, tradeoffs, open decisions and next implementation
   step in the existing plan or task record.
7. When implementation is authorized, implement the design. If it repeatedly needs exceptions,
   revisit the design rather than adding more escape hatches.

Before handing off a design, trace one successful operation and one failure
through its signatures. For asynchronous or durable work, show who claims,
acknowledges, fails and retries it, and which transactions can commit
independently. Fix signatures that cannot support those sequences.

For substantial feature or issue delivery, use
[plans and authority](../follow-instructions/references/approved-plans.md).
Update changed decisions under those rules; a new discovery alone does not
require another approval. Design-only and small local tasks retain their scope.

Use `references/rationale-template.md` when a separate decision record is needed;
its sections are optional prompts. Read `references/design-red-flags.md` when
comparing module boundaries or reviewing a proposal. For asynchronous saves,
conflicts, retries, shared views or owned resources, read
[state and lifecycle boundaries](references/state-and-lifecycle.md).
