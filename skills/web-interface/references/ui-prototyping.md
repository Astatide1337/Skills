# UI Prototyping

Use when the user wants to compare visual directions or when a relevant UI
decision needs a clickable prototype under the
[approved-plan contract](../../follow-instructions/references/approved-plans.md).
A prototype answers a design question and does not establish production readiness.

## Choose the host

Prefer an adjustment to an existing page. Real navigation, data shape, density,
tokens, and surrounding UI make the comparison more trustworthy. Keep the
prototype in an isolated copy or an existing authorized preview, use the actual
application's components and conventions, and visibly mark it as temporary.
Record source/preview identity and owned cleanup. A standalone visual imitation
cannot satisfy the actual-component gate; an unavailable host remains pending.

Create a new throwaway route only when no plausible host exists. Follow the
project's current routing convention and avoid introducing a second framework,
build system, or design language.

## Build the flow or comparison

1. State one decision question and its success criteria.
2. Use one recommended clickable flow when alternatives are not the decision.
   For a comparison, default to two or three variants; cap at five.
3. When comparing, make variants structurally distinct. Change hierarchy,
   layout, information density, navigation or the primary affordance rather
   than merely colors or labels.
4. Keep shared facts constant: use the same representative data, domain copy,
   surrounding chrome, and product constraints unless the question tests one
   of them.
5. Render the variants in the real surface. Keep the active variant shareable
   and stable across reload/Back/Forward using the host framework's URL query
   conventions.
6. Add a temporary switcher only for competing directions; it must identify each
   direction without overlapping or altering the surface being judged. Make
   relevant loading, empty, error and success states reachable and labeled.
7. Ensure each variant can be reached directly without clicking through an
   unrelated setup flow.

Keep real mutations out of the prototype unless the question explicitly
concerns mutation behavior. Use local/in-memory state and representative data;
do not add persistence, analytics, migrations, or production APIs just to make
the prototype feel complete.

## Evaluate

For each direction, exercise the same relevant states and viewport/theme
conditions. Compare against the stated question rather than selecting the most
polished-looking option by default.
For a single flow, exercise its controls and relevant states at the affected
wide/narrow viewports. Capture and inspect the actual render; a compile check
or source sketch cannot prove the interaction. Link the preview and evidence
from the approval HTML and state what remains illustrative or untested.

Record:

- what the variant changes;
- what it makes easier or harder;
- accessibility or responsive constraints;
- implementation implications that materially affect the decision;
- the selected direction and why.

Do not spend time on production abstractions, exhaustive error handling, or
tests unrelated to the design decision. The prototype must still be runnable
and honest enough to answer its question.

## Resolve and clean up

Once a direction is selected:

1. Capture the decision and evidence in the project's normal decision record,
   issue, or implementation context.
2. After implementation approval, fold the winner into normal production code
   with appropriate data, accessibility, tests and verification.
3. Remove losing variants, the temporary route, switcher, and prototype-only
   state.
4. Preserve any explicitly accepted details while iterating on the rest.

Do not let the prototype become an undocumented permanent second interface.
Logic/state-machine prototyping remains outside `web-interface`.
