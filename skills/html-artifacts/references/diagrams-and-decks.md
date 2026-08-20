# Diagrams and decks

## Technical diagrams

Use inline SVG when exact placement, styling, or interaction matters. Use HTML
and CSS for simple timelines or aligned flows. Avoid a diagram when a short
sequence or table is clearer.

- Give SVG a `viewBox`, a programmatic name, and a useful description.
- Use groups with stable IDs or classes so humans can edit the source.
- Keep labels as text, not paths or raster images.
- Use arrowheads and explicit direction; distinguish paths with labels, shape,
  or line style as well as color.
- Highlight the common path and collapse rare detail instead of drawing a
  complete dependency hairball.
- Keep one visual language across a figure set: type, line weight, nodes,
  arrowheads, and semantic color.
- Provide “Copy SVG” or download when figures are intended for reuse.

For interactive diagrams, the chart is navigation and an adjacent panel holds
details. Every clickable node must also be focusable and keyboard operable.

## Slide decks

Use a deck only for narrated material with distinct beats. Dense material meant
for self-study belongs in a report.

- Use one full-viewport section per slide and one idea per slide.
- Support previous/next buttons as well as arrow keys and Space.
- Show slide number and total. Preserve the current slide in the URL hash so a
  refresh or shared link returns to the same place.
- Fit a stable 16:9 stage with letterboxing instead of allowing layout to shift.
- Provide visible fullscreen control and do not require fullscreen.
- Keep speaker notes hidden from the projected view but reachable with a clear
  control when requested.
- Disable transitions for reduced motion and tolerate fast repeated navigation.
- Ensure navigation controls and slide content remain usable on touch screens.

## Verification

Inspect the first, densest, and last slide at common laptop and projector
dimensions. Traverse the entire deck forward and backward with keyboard and
buttons. For diagrams, test zoom, narrow layouts, labels, focus order, and any
copy or detail-panel action.
