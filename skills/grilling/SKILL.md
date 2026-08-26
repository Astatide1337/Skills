---
name: grilling
description: Pressure-test a plan or design before implementation, including its assumptions, risks, tradeoffs, and failure modes.
---

# Grilling

Choose the mode from the request.

## Interactive mode

Build a decision tree for the proposal. Each node is a decision whose answer
may expose dependent decisions. Find the current frontier: unresolved decisions
that can be answered independently with the evidence already available. Ask
that frontier as one short numbered round rather than serializing independent
questions across many turns.

For every question:

- explain the consequence of leaving it unresolved;
- give a recommended answer and the reason for it;
- distinguish a user-owned product or risk decision from a fact the agent can
  investigate;
- offer bounded alternatives when the recommendation is not clearly dominant.

Wait for the answers, update the decision tree, and repeat with the newly
exposed frontier. Follow an answer into its weakest assumption when it changes
the shape of the plan. Do not ask the user for facts that available read-only
evidence can establish.

Before sending a round, scan every relevant dimension named below. Include all
independent high-consequence decisions already exposed by the proposal; do not
defer identity or shared-resource authority, recovery, or rollout merely to
keep the round short. Defer only decisions that genuinely depend on an answer
from the current frontier.

## One-response mode

When the user asks for a complete pressure test in one response, return a
compact map of the highest-consequence assumptions, concrete failure modes,
and the smallest experiments that discriminate between plausible outcomes.

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
