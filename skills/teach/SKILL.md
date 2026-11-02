---
name: teach
description: "Explains code so the user can maintain it, combining how it works with why it was built that way. Use when the user wants to understand, learn or own a change or subsystem."
---

# Teach

Use `how` to explain behavior and `why` to explain design decisions when both
matter. Match the depth to the user's question and what they already know.
Start with the shortest explanation that answers it; add detail when needed or
requested.

Choose useful teaching aids:

- a before-and-after walkthrough with representative inputs and results;
- the modules that receive, validate, change, store and return data;
- an explanation of why ordering or a boundary matters;
- a worked concurrency, partial-failure or recovery case;
- a concise model the user can use when making later changes.

For a change, compare the old and new execution paths. For maintenance, work
through a likely failure, show where to investigate first, and finish with the
key relationship the user should remember. Distinguish what the supplied code
establishes from what remains unknown.

Use code or diagrams when they clarify the explanation. Build a complex diagram
in stages. Ask a check-for-understanding question only when the user requests
interactive teaching.

Write conversationally. Keep symbol lists and framing out of the way of the
answer. Preserve `why`'s distinction between evidence, inference and uncertainty.
Use `unslop` for the final explanation.
