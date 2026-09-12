# Experience and communication

This local reference adapts pstack's Experience First principle and connects it
to principal-level communication and teaching.

## Trigger

Use when a product journey, API consumer, error state, documentation, review
handoff, or cross-team decision affects a person using or maintaining the
result.

## Decision rule

Optimize the complete consumer journey, not implementation convenience or a
feature count. Make errors actionable, preserve accessible interaction, and
explain the decision so another engineer can act without reconstructing the
whole investigation. Treat the next maintainer and API consumer as users too.

## Procedure

1. Name the user or maintainer and the core task they need to complete.
2. Identify loading, empty, success, error, keyboard, accessibility, and
   recovery states that are relevant to that task.
3. Prefer a smaller coherent journey over several rough options. Prototype only
   when the experience or architecture is genuinely uncertain.
4. Explain the meaningful trade-off, data flow, and ownership in the handoff.
5. Use the existing project/browser tools to exercise the relevant state. A
   screenshot, prose claim, or static markup is not runtime proof by itself.

## Principal-engineer lens

Principal impact is multiplied through understanding. Clear explanations,
teachable decisions, and interfaces that make the right action obvious reduce
coordination cost across people and teams.

## Evidence

For UI, record the actual interaction and relevant visual/accessibility result.
For APIs and libraries, show the caller-facing contract and error behavior. For
reviews or teaching, link the source and distinguish observed facts from
inferred rationale.

## Example

A form validation failure should focus the actionable summary and link to the
invalid field, not merely change the field's color. A backend-only correction
does not need a browser session when no UI state changed.

## Limit

Do not force a product-design exercise onto a spelling fix or a local parser.
Do not call visual polish evidence of behavior that was never exercised.
