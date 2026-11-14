---
name: agent-contracts
description: "Use when authoring or revising a substantial implementation spec or an explicitly requested agent contract. Tiny corrections and research/review briefs use their existing compact records."
---

# Agent Contracts

Own the spec format, requirement/assumption IDs and readiness confidence. Use the
[full template and grammar](references/contract.md) when the existing
[plans trigger](../follow-instructions/references/approved-plans.md) applies or a
spec is explicitly requested. Inspect authoritative inputs before drafting.
Keep requirement conditions and acceptance observable; distinguish facts from
assertions. Resolve ordinary factual unknowns with bounded authorized discovery.

The existing task record holds the canonical spec by default. When portability
or versioned review needs a file, keep one Markdown source outside the checkout
in the task's private artifacts and record its location. HTML is a review view
identifying the canonical source and revision, never another editable authority.
No committed plan or new approval gate is required.

Tiny corrections use compact outcome/inputs, scope/authority, acceptance and
confidence in the task record; add design/assumptions only when material.
Research, review and explanation retain their bounded briefs. These records
need neither twelve headings nor the file validator.

For file-backed full specs, run the read-only structural check before claiming
format validity:

```sh
python3 skills/agent-contracts/scripts/validate_spec.py /absolute/private/spec.md
```

It reads UTF-8, emits JSON errors/assumption diagnostics and exits 0 for valid
structure, 1 for structural errors, 2 for invocation/read errors. It writes
nothing and uses no network. It cannot establish semantic truth, authorization,
feasibility or runtime enforcement. Fix structural errors without changing
acceptance to evade a check. Unresolved/refuted assumptions are valid documented
planning states: inspect their evidence and affected R-IDs, resolve or explicitly
block dependent work, and continue only unaffected authorized work.

Keep assignments, return envelopes and revision recovery with
[parallel](../follow-instructions/playbooks/parallel.md); the template links the
single Orchestration definition. Workers propose changes; only the integrating
owner issues revisions within existing authority. Full access is an execution
mode, separate from task authority. A revision never replenishes a budget.

## Confidence

Assess readiness of this exact revision for the next authorized stage. Record
an integer 1–10, assessor, evidence basis, principal uncertainty and next evidence
that would change it. Use these local anchors:

- 1–2: intended outcome or essential constraints are not established.
- 3–4: plausible approach; key source, interface or acceptance facts missing.
- 5–6: grounded and checkable; material feasibility/design assumptions unresolved.
- 7–8: relevant code/constraints inspected; requirements, design and acceptance
  align; explicit bounded uncertainties remain.
- 9–10: independent challenge and representative feasibility/failure checks
  support the spec; no known material gap remains at the assessed scope.

Scores are judgments, never probabilities, authority or arithmetic averages.
Missing authorization or a blocking prerequisite remains blocking at 9 or 10.
For example, 7 can support local adapter work with inspected callers while an
untested remote dependency still blocks claiming remote integration complete.
Name the affected stage. Reassess after material evidence or revision changes;
do not add repeated confidence announcements to ordinary chat.
