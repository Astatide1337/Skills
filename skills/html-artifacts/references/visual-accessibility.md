# Visual and accessibility baseline

## Establish a visual system

If the surrounding project has tokens, typography, or an established visual
identity, derive a small set of artifact variables from that source. Do not
copy an application shell when the artifact is a document.

Without an existing system, choose a clear editorial direction:

- one body family, one display family when justified, and one monospace family;
- a readable body size and line height with prose near 60–75 characters;
- one semantic accent plus explicit success, warning, and danger treatments;
- a spacing scale, thin rules, and restrained surfaces;
- decoration subordinate to evidence and navigation.

Avoid the default generated-dashboard look: repeated floating cards, purposeless
gradients, excessive rounding and shadows, centered body copy, emoji headings,
placeholder logos, and decorative metrics. A table, timeline, diagram, or strong
typographic page should look like its actual genre.

## Accessibility baseline

- Use landmarks and native elements before ARIA.
- Keep headings logical and provide a skip link when navigation precedes long
  content.
- Give controls accessible names, visible focus, useful target size, and a
  keyboard path. Do not make hover the only way to reveal necessary content.
- Associate labels, instructions, errors, and status messages with controls.
- Announce copied, exported, filtered, or validation results through a polite
  live region where appropriate.
- Meet WCAG AA contrast for normal text and meaningful interface graphics.
- Do not encode categories or severity with color alone.
- Make tables responsive without destroying header relationships. Prefer local
  overflow to shrinking text below readability.
- Give meaningful images alternative text. Treat decorative images as such.
- Respect text zoom, reduced motion, forced colors, and light/dark preferences
  when the artifact supports them.

## Responsive behavior

Start with the narrow reading order. Enhance to columns or side annotations
only when width permits. Use fluid type and spacing conservatively; cap content
width for prose while allowing diagrams and comparisons to use more space.

Test at least one narrow phone width and one wide desktop width. Inspect the
longest heading, widest table, deepest code block, densest diagram, and every
fixed or sticky element. Printing matters for reports: add print styles when a
reader is likely to save or circulate a PDF.

## Factual design

The visual hierarchy must match epistemic status. Clearly distinguish measured
results, claims, estimates, unknowns, and recommendations. Do not let polished
presentation make weak evidence look conclusive.
