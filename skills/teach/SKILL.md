---
name: teach
description: Teach a code change or subsystem in plain language so the user can work with it. Use when the user asks to learn, understand deeply, or be walked through code rather than merely receive a reference answer.
---

# Teach

Use `how` for mechanics and `why` for rationale when both matter. Match depth to why the user is asking and what the conversation shows they already know.

Start with the smallest complete explanation, but make it maintainable rather
than merely accurate:

1. Give one concrete before/after walkthrough with representative inputs and
   observable outcomes.
2. Trace ownership and data flow: who receives, decides, mutates, persists, and
   returns.
3. Explain why ordering and boundaries matter.
4. Work through one realistic concurrency, partial-failure, or recovery case
   step by step.
5. Separate guarantees proved by the supplied code from missing details.
6. End with a one-sentence mental model and one self-check question that tests
   transfer, not trivia.

Show code or a diagram only when it makes the mechanism easier to grasp. For
several moving parts, build the picture in small stages instead of presenting
one crowded diagram.

Keep it conversational. Do not quiz, perform pacing theater, dump symbol lists, or bury the answer in framing. Preserve `why`'s confidence labels and uncertainty. Write the final explanation through `unslop`.
