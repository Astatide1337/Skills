# Design red flags

## Shallow modules

A useful module hides substantial policy or mechanism behind a small coherent
interface. A shallow module exposes nearly as much complexity as it contains.
Do not confuse a deep call chain with a deep abstraction: several tiny wrappers
can force callers to understand every layer while none owns the decision.

Ask what knowledge the caller no longer needs because this module exists. If
the answer is "none," remove or deepen the boundary.

## Information leakage

A boundary leaks when multiple modules must know the same storage layout, wire
format, sequencing rule, validation detail, or failure convention. Publicly
exposing database rows or transport payloads often freezes implementation
choices into callers.

Move shared knowledge to the module that owns the invariant. Translate at the
boundary instead of making every consumer understand an external form.

## Temporal decomposition

Modules named after execution stages such as `read`, `transform`, and `write`
often split one piece of knowledge across the call chain. Prefer ownership by
domain knowledge or invariant when stages always change together. A pipeline is
appropriate when stages are independently replaceable and communicate through
a stable contract.

## Pass-through layers

A method that forwards the same arguments and result without enforcing policy,
translating representations, stabilizing an interface, or owning failure adds a
place to navigate rather than an abstraction. Remove it or give the layer a
real responsibility.

## Speculative generality

Do not introduce plugins, generic repositories, event buses, factories, or
configuration axes for imagined consumers. Name the second real use case and
show how it differs. Preserve a seam when substitution is likely; avoid
implementing all future variants now.
