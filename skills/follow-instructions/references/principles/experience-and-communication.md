# Experience and communication

Adapted from pstack's Experience First principle for product work, API design,
documentation and teaching.

## Trigger

Use when a product journey, API consumer, error state, documentation, review
handoff, or cross-team decision affects a person using or maintaining the
result.

## Decision rule

Make the complete task work for the person or caller using the result. Make
errors actionable, preserve accessible interaction, and explain the decision so
another engineer can act without reconstructing the whole investigation. Treat
the next maintainer and API consumer as users too.

## Procedure

1. Name the user or maintainer and the core task they need to complete.
2. Identify loading, empty, success, error, keyboard, accessibility, and
   recovery states that are relevant to that task.
3. Prefer a smaller coherent journey over several rough options. Prototype only
   when the interaction or architecture is uncertain.
4. Explain the meaningful trade-off, data flow, and ownership in the handoff.
5. Use the existing project/browser tools to exercise the relevant state. A
   screenshot, prose claim, or static markup is not runtime proof by itself.

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
