---
name: grilling
description: Interrogate a plan or design before implementation. Use when the user asks to grill, challenge, pressure-test, or expose hidden assumptions in an approach.
---

# Grilling

In an interactive interrogation, ask one consequential question at a time and
follow each answer into its weakest assumption. When the user asks for a
one-response pressure test, do not stop after one question: return a compact
map of the highest-consequence assumptions, concrete failure modes, and the
smallest experiments that discriminate between plausible outcomes.

Cover, as relevant: intended outcome, users, constraints, ownership, data model, failure modes, security, operability, migration, rollback, cost, and what is deliberately excluded. When an answer depends on a fact, inspect the available evidence with read-only tools; delegate only when the environment permits and it is genuinely useful.

Do not start implementing or silently replace the proposal with your preferred
architecture. Separate blockers from tolerable risks and reversible choices.
Keep a compact decision log of confirmed decisions, unresolved risks, and
assumptions that need evidence. Stop when the plan is coherent enough to execute
or the user asks to stop. End with decisions, remaining unknowns, focused
experiments, and the first concrete next step.

Before finishing a one-response grill, scan the relevant dimensions named
above once. Any omitted dimension must be marked irrelevant with a reason, not
silently skipped—especially identity/authorization, observability, recovery,
and staged rollout, which often disappear behind the primary technical risk.
