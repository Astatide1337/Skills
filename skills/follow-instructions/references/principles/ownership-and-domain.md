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
