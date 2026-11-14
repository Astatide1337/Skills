---
name: agent-contracts
description: "Use when authoring or revising a substantial implementation spec or an explicitly requested agent contract. Tiny corrections and research/review briefs use their existing compact records."
---

# Agent Contracts

Use this skill for the spec format, requirement and assumption IDs, and
confidence in the spec's readiness. Use the
[full template and grammar](references/contract.md) when the existing
[plans trigger](../follow-instructions/references/approved-plans.md) applies or a
spec is explicitly requested. Inspect authoritative inputs before drafting.
State each requirement's conditions and expected result so they can be checked.
Distinguish observed facts from assertions. Resolve factual unknowns through
scoped observations within the task's authority.

Keep the canonical spec in the existing task record by default. If another agent
needs a portable file or a reviewer needs a versioned copy, keep one Markdown
source in the task's private artifacts outside the checkout. Record its location
in the task. When presenting it as HTML, identify the source and revision; make
edits in the source. Writing a spec does not require a commit or approval beyond
the task's existing rules.

For tiny corrections, record the outcome, inputs, scope, authority, acceptance
and confidence briefly in the task record. Add design decisions or assumptions
only when material.
Research, review and explanation retain their bounded briefs. These records
need neither twelve headings nor the file validator.

For file-backed full specs, run the read-only structural check before claiming
format validity. Resolve `<skill-dir>` to the absolute directory containing this
SKILL.md, using the supplied skill location rather than the project directory:

```sh
python3 "<skill-dir>/scripts/validate_spec.py" /absolute/private/spec.md
```

The validator reads UTF-8 and reports errors and assumption diagnostics as JSON.
It exits 0 for valid structure, 1 for structural errors, and 2 for invocation or
read errors. It writes
nothing and uses no network. It cannot establish semantic truth, authorization,
feasibility or runtime enforcement. Fix structural errors without changing
acceptance to evade a check. Unresolved/refuted assumptions are valid documented
planning states: inspect their evidence and affected R-IDs, resolve or explicitly
block dependent work, and continue only unaffected authorized work.

Keep assignment and result formats, and recovery from stale revisions, with
[parallel](../follow-instructions/playbooks/parallel.md); the template links the
single Orchestration definition. Workers propose changes; only the integrating
owner issues revisions within existing authority. Full access is an execution
mode, separate from task authority. A revision never replenishes a budget.

## Confidence

Assess whether this exact revision is ready for the next authorized stage.
Use the template's fields: `Score` (an integer from 1 to 10), `Assessor`,
`Basis` (supporting evidence), `Uncertainty`, and `Next evidence` (what would
change the score).
Use these local anchors:

- 1–2: intended outcome or essential constraints are not established.
- 3–4: plausible approach; key source, interface or acceptance facts missing.
- 5–6: grounded and checkable; material feasibility or design assumptions unresolved.
- 7–8: relevant code and constraints inspected; requirements, design and acceptance
  align; explicit bounded uncertainties remain.
- 9–10: independent challenge and representative feasibility and failure checks
  support the spec; no known material gap remains at the assessed scope.

Treat the score as an evidence-backed judgment. Do not interpret it as a
probability, calculate it as an arithmetic average, or use it to grant
authority. A score of 9 or 10 does not resolve missing authorization or a
blocking prerequisite.
For example, 7 can support local adapter work with inspected callers while an
untested remote dependency still blocks claiming remote integration complete.
Name the affected stage. Reassess after material evidence or revision changes;
do not add repeated confidence announcements to ordinary chat.
