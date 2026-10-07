# Ownership and domain

This local reference combines pstack's Foundational Thinking, Model the
Domain, Boundary Discipline, and Type System Discipline. The existing
`architect` and security skills remain the detailed owners for their domains.

## Trigger

Use before changing shared behavior, a public interface, stateful logic, or a
system where the same shape assumption appears in several files.

## Decision rule

Find the authoritative state, callers, lifetime, writers, and contract before
editing. Choose the data shape before branching logic. Parse and validate
untrusted data at the boundary, then let internal code rely on the resulting
domain type. Put behavior with the owner of its invariant, not with whichever
layer happens to call it first.

## Procedure

1. Trace one real caller from input to output and list the affected consumers.
2. Identify who owns the data, who may write it, and which interface must stay
   stable.
3. Choose a structure that represents the domain. Use a state machine,
   discriminated variant, registry, queue, or plain local code only when it
   removes a real invalid state or repeated rule.
4. Validate external values once at the boundary. Do not export transport,
   storage, or framework representations as the domain contract.
5. Check concurrent writers and lifecycle transitions before sharing mutable
   state.
6. Implement at the owning layer and verify the caller's observable behavior.

## Principal-engineer lens

Principal-level architecture is often ownership management. The question is
not only “what code is shortest?” but “who owns this invariant, who can change
it, and what other teams or callers inherit?” Clear ownership reduces future
coordination cost.

## Evidence

Keep a source path, type/signature, and caller-level check. For a cross-process
or external boundary, record the identity and state owner. A diagram without a
real caller or failure path is not enough.

## Example

If an MCP handler calls a domain pagination function, fix the cursor contract in
that domain function. Do not duplicate cursor rules in the transport and then
ask two owners to remain synchronized.

## Limit

A small, already-clear local correction does not require a new abstraction,
branded type, or architecture document. Strengthen the model where a partial
state or repeated assumption causes a real risk.

## Construction decisions and counterexamples

Use these examples when choosing or reviewing a boundary/data shape; do not
turn every local edit into a design exercise. Existing repository contracts win.

| Trigger | Prefer | Reject | Evidence and legitimate near-miss |
| --- | --- | --- | --- |
| External input enters domain logic | Parse into the needed internal shape using the existing schema/parser; reject malformed data at entry. | A cast or repeated downstream fallback that hides a malformed value. | Valid and malformed-input tests through the caller; portable TypeScript lint catches some unsafe conversions. A type guard still needs runtime tests. Ignore irrelevant metadata when the contract permits it. |
| Fields describe mutually exclusive states | A variant with the fields belonging to each legal state. | Independent flags/optional fields that permit contradictions and then need scattered repair. | Exercise each legal transition and an invalid transition. Keep a plain boolean or list when all operations remain defined; brands and state machines need an actual invalid-state risk. |
| More than one surface derives the same state | One authoritative state and shared policy for its derived views. | Copies that require synchronization or disagree after archive/restore. | Drive the same transition through both real consumers; use existing selectors where present. Separate state is valid when the two concepts are independent. |
| A save/retry/cancellation can commit | The existing [state/lifecycle procedure](../../../architect/references/state-and-lifecycle.md). | Treating a hidden UI as rolled-back persistence or an uncertain timeout as permission to repeat a write. | Pre/post-commit and retry observations at the owning boundary; static lint is insufficient. |
| A proposed layer has one trivial caller | Direct code or the existing owner until another real use case needs the layer. | Generic repositories, factories or wrappers that merely forward values. | Trace the caller and name the decision hidden by each layer. A one-caller adapter is useful when it isolates an actual external protocol or failure boundary. |

For TypeScript, rely on checked narrowing and exhaustive variants rather than
asserting a desired type. Supplemental checks live in
[portable lint](../../../code-review-and-quality/references/portable-lint.md);
compiler/native project checks remain necessary. Do not ban all `as` syntax or
force branded types into an already-total function. Architecture and complete
runtime validation remain judgments, not installed universal lint rules.

These construction choices adapt P-stack's
[TypeScript guidance](https://github.com/cursor/plugins/blob/7022c81efb48d8b5eb15498ce6043a3bd74b694c/pstack/skills/typescript-best-practices/SKILL.md)
and the original audit's boundary misclassification, divergent views and discarded
drafts. Those audit mappings motivate tests; they do not certify the original
applications fixed or establish a principal-engineer quality score.
