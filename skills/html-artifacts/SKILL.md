---
name: html-artifacts
description: When creating or revising a self-contained HTML artifact.
---

# HTML Artifacts

Choose HTML because it improves the work, not because it makes the response
look elaborate. Produce a complete artifact that opens directly, explains
itself, and remains useful outside the conversation.

## Lock the deliverable

Default to a dedicated directory directly beneath `/tmp`, created with
`mktemp -d`, so disposable artifacts do not dirty a repository. Write, validate,
open and finally link the artifact from that directory. An explicit user output
path takes precedence; preserve it without adding an unrequested second copy.

Preserve an explicitly requested filename. When no filename is supplied, choose
a descriptive kebab-case `.html` filename inside the dedicated directory.

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
The coordinator's [approved-plan contract](../follow-instructions/references/approved-plans.md)
explicitly requires HTML for nontrivial engineering approval; use its content
requirements rather than reconsidering the medium or duplicating approval rules.

## Route by artifact

Read only the references needed for the request:

| Deliverable | Read |
| --- | --- |
| Report, research brief, comparison, plan, review, post-mortem | [Document patterns](references/document-patterns.md) |
| Interactive explainer, prototype, tuner, triage tool, custom editor | [Interactive artifacts](references/interactive-artifacts.md) |
| Architecture diagram, flowchart, technical figure, slide deck | [Diagrams and decks](references/diagrams-and-decks.md) |
| Any artifact's visual system, responsive behavior, or accessibility | [Visual and accessibility baseline](references/visual-accessibility.md) |
| Matching an existing product, report family, or personal visual language | [Style matching](references/style-matching.md) |

For application UI or reusable product components, hand visual and interaction
decisions to `web-interface`; this skill owns the standalone document and its
packaging. An artifact may borrow the product's tokens without becoming part of
the product.

## Universal contract

Every artifact must:

1. Exist at the explicit authorized output path or beneath the dedicated `/tmp`
   directory for this task. Preserve a requested filename, or choose one
   descriptive kebab-case `.html` filename. Resolve the final path before writing
   and check that it remains within the authorized output boundary.
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
   supplied examples when they exist; otherwise select a restrained typographic
   direction. Use layout, type, and a small semantic palette consistently.
3. **Sketch information architecture.** Decide what must be visible at first
   glance, what compares side by side, what can collapse, and how the reader
   navigates on mobile.
4. **Implement the smallest complete file.** Resolve the authorized output path;
   absent an explicit path, create and confirm a dedicated `/tmp` folder. Prefer
   platform HTML, CSS, and JavaScript. Add interaction only when it reduces
   cognitive or mechanical work. Preserve an explicit filename and output path.
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
