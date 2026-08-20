# Document patterns

Select the layout that exposes the document's reasoning. Keep prose concise and
use visual structure only where it carries information.

## Reports and research briefs

- Lead with the conclusion, confidence, scope, and date.
- Separate observed evidence, interpretation, unknowns, and recommendations.
- Use a compact evidence matrix when several checks support different claims.
- Put citations next to the claims they support; make links descriptive.
- Use charts only when they reveal a relationship. Label units, time ranges,
  sources, and whether values are measured or estimated.
- End with the narrowest next action, not a generic summary.

For status reports, make shipped, active, blocked, and requested decisions
scannable without relying only on color. For incident reports, use a real
timestamped timeline as the spine, followed by customer impact, causal chain,
what helped, what hindered, and owned follow-ups.

## Comparisons and decisions

- Give every option the same fields and evidence standard.
- Place two or three options in aligned columns at wide widths and stack them
  with persistent labels on narrow screens.
- Compare concrete constraints, operational cost, reversibility, and failure
  modes—not invented numeric scores.
- Make a recommendation when evidence supports one; otherwise name the exact
  unresolved question.

## Plans and specifications

- Show stages as a dependency-aware sequence, not decorative numbered cards.
- Add a diagram only when three or more components or branches interact.
- Pair risks with observable mitigations and validation evidence.
- State exclusions and decision points explicitly.
- Keep file lists subordinate to ownership and runtime flow.

## Code reviews and technical explainers

- Lead with high-impact findings or the subsystem's hot path.
- Anchor review notes to file and line evidence when available.
- For diffs, keep code visually continuous and place annotations beside the
  relevant lines. Use text labels as well as severity colors.
- For module maps, show entry points, ownership boundaries, the common path,
  and one representative data lifecycle. Omit incidental imports.
- Never imply code, tests, CI, or a live system was inspected unless evidence
  supports the claim.

## Common failures

- Recreating Markdown headings inside decorative containers.
- Hiding the conclusion below a hero section.
- Filling whitespace with invented KPIs, progress rings, or charts.
- Giving unlike options unlike evaluation criteria.
- Using interaction to conceal information that should simply be visible.
