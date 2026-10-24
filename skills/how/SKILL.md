---
name: how
description: "Traces how code actually works: entry points, call flow, data, side effects and boundaries, with source links. Use when asked how something works or to explain or critique a subsystem."
---

# How

Explore the actual code and produce a working mental model, not an annotated file dump.

1. State the scope you inferred.
2. Find the entry point, then trace callers, callees, data transformations, types, configuration, and side effects.
3. Map the subsystem's boundaries and ownership. Read implementations; do not infer behavior from names.
4. Reconcile contradictions by checking code and tests.
5. For critique requests, explain the current system first, then assess abstraction fit, data model, boundary discipline, evolution cost, complexity, and consistency.

For complex systems, split the exploration into distinct angles locally or with read-only collaborators when available and permitted. Do not require a particular model or delegation mechanism.

Explain the flow and locations needed to answer the question, with clickable
source links and material caveats. Choose the depth and structure for this
reader. Use a diagram when it makes the mechanism clearer.

Read `references/critique-rubric.md` before making architectural judgments in
critique mode.
