---
name: html-artifacts
description: Create or revise a polished, self-contained HTML artifact when the requested deliverable benefits materially from spatial layout, visual hierarchy, inline diagrams, interaction, presentation mode, or exporting edited state. Use for HTML reports, comparisons, plans, architecture or flow explainers, annotated reviews, incident timelines, slide decks, interactive demonstrations, and one-off editors. Also use when the user explicitly asks for an HTML artifact or standalone HTML report. Do not use for ordinary chat answers, code-only output, maintained application UI, simple prose that is clearer as Markdown, or artifacts whose primary format must remain easy to diff.
---

# HTML Artifacts

Choose HTML because it improves the work, not because it makes the response
look elaborate. Produce a complete artifact that opens directly, explains
itself, and remains useful outside the conversation.

## Lock the deliverable

Extract the exact requested output path before designing. Write, validate,
open, and finally link that same path. Never rename an explicit deliverable to
match the title or subject. If the request says `report.html`, completion means
`report.html` exists—not a more descriptive alternative.

## Decide the medium

Use a standalone HTML artifact when one or more of these are load-bearing:

- readers must compare parallel options or before/after states;
- position, sequence, hierarchy, or color carries meaning;
- an inline diagram, timeline, diff, or live demonstration replaces prose;
- the reader needs to filter, reorder, tune, annotate, or export state;
- the result will be presented, revisited, or shared as a document.

Stay with Markdown for a short answer, linear prose, commands, a code snippet,
or a source document expected to receive frequent line-based review. Do not
silently turn every plan, explanation, or summary into HTML. If the format is
ambiguous, estimate whether HTML changes comprehension or enables an action;
otherwise prefer the simpler medium.

## Route by artifact

Read only the references needed for the request:

| Deliverable | Read |
| --- | --- |
| Report, research brief, comparison, plan, review, post-mortem | [Document patterns](references/document-patterns.md) |
| Interactive explainer, prototype, tuner, triage tool, custom editor | [Interactive artifacts](references/interactive-artifacts.md) |
| Architecture diagram, flowchart, technical figure, slide deck | [Diagrams and decks](references/diagrams-and-decks.md) |
| Any artifact's visual system, responsive behavior, or accessibility | [Visual and accessibility baseline](references/visual-accessibility.md) |

For application UI or reusable product components, hand visual and interaction
decisions to `web-interface`; this skill owns the standalone document and its
packaging. An artifact may borrow the product's tokens without becoming part of
the product.

## Universal contract

Every artifact must:

1. Use the exact output path and filename requested by the user. When none is
   supplied, choose one descriptive, kebab-case `.html` file. Treat the path as
   part of the deliverable and verify that exact file before reporting it.
2. Work offline with embedded CSS and JavaScript. Use inline SVG or data URIs
   for essential images. External links may be references, but external fonts,
   scripts, stylesheets, APIs, and runtime assets may not be required.
3. Use semantic HTML, a unique title, document language, viewport metadata,
   logical headings, keyboard-operable controls, visible focus, and sufficient
   contrast. Do not use color as the sole carrier of meaning.
4. Adapt from a narrow to a wide viewport without clipped content or mandatory
   horizontal page scrolling. Wide tables and code regions may scroll locally.
5. Make the content's real structure visible. Do not wrap a Markdown document
   in cards or manufacture dashboard metrics.
6. State provenance, timestamps, uncertainty, and verification boundaries when
   they affect interpretation. Never invent data to complete a visual.
7. Keep one source of truth for repeated values. Derive summary counts, filtered
   rows, and exports from the same data rather than copying totals into markup.
   Check the initial totals and one filtered state against the supplied evidence.
8. Give stateful tools an explicit export path—copy or download as Markdown,
   JSON, CSV, SVG, or another useful portable representation.
9. Avoid destructive or surprising browser behavior. Do not transmit entered
   data, request credentials, or depend on storage unless the user explicitly
   needs persistence and the artifact explains it.

## Build workflow

1. **Define the reading task.** Identify the audience, the decision or action,
   source material, required sections, and whether the artifact is read-only or
   interactive.
2. **Choose one visual grammar.** Derive tokens from an existing codebase or
   select a restrained typographic direction. Use layout, type, and a small
   semantic palette consistently.
3. **Sketch information architecture.** Decide what must be visible at first
   glance, what compares side by side, what can collapse, and how the reader
   navigates on mobile.
4. **Implement the smallest complete file.** Prefer platform HTML, CSS, and
   JavaScript. Add interaction only when it reduces cognitive or mechanical
   work. Before writing, copy any explicit output path from the request rather
   than renaming it from the document's subject.
5. **Validate the source.** Run:

   ```bash
   python skills/html-artifacts/scripts/check_artifact.py path/to/artifact.html
   ```

6. **Inspect the render.** Open the actual file, capture the relevant wide and
   narrow states, and inspect hierarchy, overflow, typography, contrast,
   controls, focus, and all exported output. For animation, watch a complete
   cycle and test reduced motion.
7. **Report evidence narrowly.** Link the file and distinguish source checks,
   rendered inspection, interaction testing, and anything not exercised.

The checker catches structural and offline-packaging failures; it cannot judge
visual quality, factual accuracy, interaction correctness, or accessibility by
itself.
