# Interactive artifacts

Interaction must shorten a real task: seeing a system change, testing a model,
or editing structured state. A static document is preferable when interaction
does not change understanding or output.

## Interactive explainers and prototypes

- Isolate the concept being demonstrated and expose only meaningful inputs.
- Show current values and the observable consequence together.
- Provide reset and replay where state or time changes.
- Keep a plain-language explanation beside the demonstration.
- If the user is selecting implementation values, render the resulting CSS,
  configuration, or code and provide a copy action.
- Respect `prefers-reduced-motion`; never require animation to access content.

For a multi-screen flow, implement the real forward/back path, preserve focus,
and provide a direct way to jump between states. Match fidelity to the question:
sequence testing does not require production polish.

## One-off editors

Design the export before the editing surface. The artifact is incomplete until
the user can take the result elsewhere.

- Preload the supplied data; do not make the user enter it twice.
- Choose controls that match the data type and show constraints at the moment
  they are violated.
- Provide keyboard shortcuts only alongside accessible standard controls.
- Show current counts, validation errors, or changed fields continuously.
- Provide reset; add undo when repeated edits are costly.
- Export a deterministic, documented representation such as Markdown, JSON,
  CSV, SVG, or a concise prompt.
- Prefer in-memory state. Use local storage only when persistence is explicitly
  useful, disclose it, namespace the key, and provide a clear-data action.

## Browser and data boundaries

- No backend, authentication, analytics, or network transmission by default.
- Do not embed secrets or sensitive source material merely for convenience.
- Clipboard and download actions must follow an explicit user gesture and show
  success or failure accessibly.
- Never replace native buttons, fields, dialogs, or drag alternatives with
  pointer-only custom elements.
- Treat imported files as untrusted input; render text with `textContent`, not
  `innerHTML`, unless it has been deliberately sanitized.

## Verification

Exercise every control, keyboard path, reset, export format, empty state, and
invalid state that the artifact exposes. Compare exported content with visible
state. Reload once to confirm the stated persistence behavior.
