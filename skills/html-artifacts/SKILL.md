---
name: html-artifacts
description: "Builds a self-contained HTML page (report, explainer, diagram, dashboard) that opens directly. Use when an HTML artifact, standalone page or visual write-up is requested."
---

# HTML Artifacts

Produce an HTML file that opens directly and contains the context a reader
needs outside this conversation. Use HTML when its layout or interaction helps
the reader complete the task.

## Lock the deliverable

Use a dedicated temporary directory outside the project, respecting the task's
configured temporary root. Write, validate, open and link the artifact there.
An explicit user output path takes precedence; preserve it without adding an
unrequested second copy.

Preserve an explicitly requested filename. When no filename is supplied, choose
a descriptive kebab-case `.html` filename inside the dedicated directory.

## Decide the medium

Use a standalone HTML artifact when:

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
For plans, follow the requested medium and decision criteria in
[plans and authority](../follow-instructions/references/approved-plans.md).
That reference owns approval requirements; the presentation format does not
create another approval gate.

## Route by artifact

Read only the references needed for the request:

| Deliverable | Read |
| --- | --- |
| Report, research brief, comparison, plan, review, post-mortem | [Document patterns](references/document-patterns.md) |
| Interactive explainer, prototype, tuner, triage tool, custom editor | [Interactive artifacts](references/interactive-artifacts.md) |
| Architecture diagram, flowchart, technical figure, slide deck | [Diagrams and decks](references/diagrams-and-decks.md) |
| Any artifact's visual system, responsive behavior, or accessibility | [Visual and accessibility baseline](references/visual-accessibility.md) |
| Matching an existing product, report family, or personal visual language | [Style matching](references/style-matching.md) |

Use `web-interface` for application UI or reusable product components. Use this
skill for standalone documents and their packaging. An artifact may borrow the product's
tokens without becoming part of
the product.

## Universal contract

Every artifact must:

1. Exist at the explicit authorized output path or in the task's dedicated
   temporary directory outside the project. Preserve a requested filename, or choose one
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
6. State sources, dates, uncertainty and what was verified when they affect
   interpretation. Never invent data to complete a visual.
7. Keep one source of truth for repeated values. Derive summary counts, filtered
   rows, and exports from the same data rather than copying totals into markup.
   Check the initial totals and one filtered state against the supplied evidence.
8. Let users copy or download a stateful tool's result as Markdown,
   JSON, CSV, SVG, or another useful portable representation.
9. Avoid destructive or surprising browser behavior. Do not transmit entered
   data, request credentials, or depend on storage unless the user explicitly
   needs persistence and the artifact explains it.

## Build workflow

1. **Define the reading task.** Identify the audience, the decision or action,
   source material, required sections, and whether the artifact is read-only or
   interactive.
2. **Choose a consistent style.** Derive tokens from an existing codebase or
   supplied examples when they exist; otherwise select a restrained typographic
   direction. Use layout, type, and a small semantic palette consistently.
3. **Arrange the content.** Decide what must be visible at first
   glance, what compares side by side, what can collapse, and how the reader
   navigates on mobile.
4. **Implement the smallest complete file.** Resolve the authorized output path;
   absent an explicit path, create and confirm a task-specific temporary folder. Prefer
   platform HTML, CSS, and JavaScript. Add interaction only when it makes the task
   easier to understand or perform. Preserve an explicit filename and output path.
5. **Validate the source.** Run:

   ```bash
   python skills/html-artifacts/scripts/check_artifact.py path/to/artifact.html
   ```

6. **Inspect the render.** Open the actual file, capture the relevant wide and
   narrow states, and inspect hierarchy, overflow, typography, contrast,
   controls, focus, and all exported output. For animation, watch a complete
   cycle and test reduced motion.
7. **Report what was checked.** Link the file and distinguish source checks,
   rendered inspection, interaction testing, and anything not exercised.

The checker catches structural and offline-packaging failures; it cannot judge
visual quality, factual accuracy, interaction correctness, or accessibility by
itself.
