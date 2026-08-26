---
name: how
description: Explain a codebase subsystem's runtime flow, ownership, boundaries, and file placement. Use for walkthroughs or “where should this live?” questions.
---

# How

Explore the actual code and produce a working mental model, not an annotated file dump.

1. State the scope you inferred.
2. Find the entry point, then trace callers, callees, data transformations, types, configuration, and side effects.
3. Map the subsystem's boundaries and ownership. Read implementations; do not infer behavior from names.
4. Reconcile contradictions by checking code and tests.
5. For critique requests, explain the current system first, then assess abstraction fit, data model, boundary discipline, evolution cost, complexity, and consistency.

For complex systems, split the exploration into distinct angles locally or with read-only collaborators when available and permitted. Do not require a particular model or delegation mechanism.

Return: overview, key concepts, step-by-step flow, where things live, and genuine gotchas. Cite clickable files and symbols. Use a small diagram only when it materially clarifies three or more moving parts.

Read `references/critique-rubric.md` before making architectural judgments in
critique mode.
