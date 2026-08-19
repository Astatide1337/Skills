---
name: why
description: Investigate why code or architecture exists using source history and available external evidence. Use for rationale, lineage, historical constraints, odd constants, defensive code, and questions that cannot be answered from current mechanics alone.
---

# Why

Code shows what happens, not why it was chosen. Anchor the question to exact files, symbols, and lines, then search available evidence: git history, commits and PRs, issues, design documents, team discussion, incidents/observability, errors, and product data. Source control is the minimum; list unavailable sources as gaps.

Use read-only access. Search broadly before narrowing. Record queries and null results. Quote sparingly with precise citations. Treat the user's proposed reason as a hypothesis, not a conclusion. Surface contradictions.

Classify every conclusion:

- **Direct:** a source explicitly states the reason.
- **Supported:** several indirect sources converge.
- **Inferred:** a reasonable but unstated interpretation.
- **Speculative:** one of several plausible stories.
- **Unknown:** searched and not found.

Return the question and code anchor, direct findings, reasonable inferences, competing hypotheses when needed, specific unknowns, sources consulted, and an overall confidence summary. Never cite code behavior as proof of author intent. Preserve uncertainty instead of completing a tidy story.

See `references/epistemics.md`.
