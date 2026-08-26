---
name: teach
description: Teach a code change or subsystem in plain language so the user can understand and work with it.
---

# Teach

Use `how` for mechanics and `why` for rationale when both matter. Match depth to why the user is asking and what the conversation shows they already know.

Start with the smallest complete explanation. Add another layer only when the
user's purpose requires it or they ask to go deeper. A short orientation may be
enough; do not force every teaching device into every answer.

Choose the few devices that best answer the user's question:

- a concrete before/after walkthrough with representative inputs and outcomes;
- ownership and data flow: who receives, decides, mutates, persists, and returns;
- why an ordering or boundary matters;
- a worked concurrency, partial-failure, or recovery case;
- a concise mental model the user can carry into later changes.

When the user asks about a change, explicitly contrast the old and new runtime
paths. When they ask to maintain the behavior, finish with the shortest useful
mental model after the worked failure seam.

Separate guarantees proved by the supplied code from missing details. When the
user wants to maintain or modify the behavior, include the likely failure seam
and where they should look first. Ask a check-for-understanding question only
when the user invites interactive teaching; do not append a quiz by default.

Show code or a diagram only when it makes the mechanism easier to grasp. For
several moving parts, build the picture in small stages instead of presenting
one crowded diagram.

Keep it conversational. Do not quiz, perform pacing theater, dump symbol lists, or bury the answer in framing. Preserve `why`'s confidence labels and uncertainty. Write the final explanation through `unslop`.
