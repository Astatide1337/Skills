---
name: how
description: "Traces how code actually works: entry points, call flow, data, side effects and boundaries, with source links. Use when asked how something works or to explain or critique a subsystem."
---

# How

Trace the code needed to answer the question and explain how the parts work
together.

1. State the scope you inferred.
2. Find the entry point. Follow calls, data transformations, types,
   configuration and side effects.
3. Identify which module owns each behavior and where control or data crosses
   boundaries. Read implementations rather than inferring behavior from names.
4. Resolve contradictions by checking code and tests.
5. For a critique, explain the current system first. Then assess its
   abstractions, data model, dependencies, change cost, complexity and consistency.

For complex systems, investigate separate questions locally or with authorized
read-only collaborators. No particular model or delegation mechanism is required.

Explain the relevant flow with source links and limitations that affect the
answer. Match the depth to the reader. Use a diagram when it clarifies the flow.

Read `references/critique-rubric.md` before making architectural judgments.
