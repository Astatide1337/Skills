---
name: why
description: Investigate why code or architecture exists using history and external evidence. Use for rationale, lineage, constraints, odd constants, or defensive code.
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

Label the confidence tier beside each material conclusion, not only in a final
summary. Include the searched scope and any meaningful null result so `Unknown`
can be distinguished from `not investigated`.

When the investigation informs a proposed change, finish by naming the current
evidence needed to know whether the historical constraint still applies. Make
it operational and specific—current configuration or enforced limit, migration
state, runtime telemetry, failure/cancellation behavior, and a safe validation
path as relevant—not merely “confirm in production.”

Use a final `Before changing this` paragraph for that evidence. Distinguish the
current enforced constraint, observed runtime behavior, and cleanup/failure
telemetry so the recommendation cannot end with historical evidence alone.

Read `references/epistemics.md` before synthesizing confidence or resolving
contradictory evidence. Read `references/code-archaeology.md` for repository
history investigations.
