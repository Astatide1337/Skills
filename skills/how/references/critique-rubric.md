# Architecture critique rubric

Explain the current mechanism before judging it. Tie every finding to a
concrete dependency, change scenario, or failure consequence. An empty critique
is valid when the design fits its needs.

## Abstraction fit

Does each abstraction hide meaningful complexity or stabilize a volatile
dependency? Flag wrappers whose callers still need to understand the wrapped
implementation. Also flag modules that combine unrelated decisions and force
changes to travel together.

## Data model and access

Do representations match the operations performed on them? Look for repeated
scans, lossy conversions, duplicated state, unclear identity, and storage or
transport types leaking through domain boundaries. Do not recommend a new data
structure without naming the access pattern it improves.

## Boundaries and testability

Are parsing, validation, authorization, side effects, and failure translation
owned at clear edges? Can policy be tested without constructing unrelated
infrastructure? Identify cycles, hidden global state, and cross-layer reach.

## Plausible evolution

Choose two or three changes the product is credibly likely to need. Trace how
many modules, contracts, and migrations each would touch. Distinguish genuine
locality from indirection that merely spreads the edit across more files.

## Complexity and value

Every layer, queue, cache, configuration option, and framework has operational
and cognitive cost. Ask which current requirement pays for it. Over-abstraction
is as real as under-abstraction; prefer the smallest design that protects real
invariants and likely change seams.

## Consistency

Compare with established repository conventions, but do not treat consistency
as automatically correct. A deviation needs a reason. A repeated local
workaround may show that the existing convention no longer fits.
