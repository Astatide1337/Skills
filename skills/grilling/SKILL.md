---
name: grilling
description: "Pressure-tests a plan, design or proposal by asking the unresolved decisions with recommended answers. Use when asked to grill, challenge, poke holes in, or stress-test an idea."
---

# Grilling

Choose interactive or one-response mode from the request. Investigate facts
available through authorized read-only access before asking the user to decide.

## Interactive mode

Map the proposal's unresolved decisions and their dependencies. Ask decisions
that can be answered independently together in one short numbered round.

For each question:

- explain what depends on the answer;
- recommend an answer and give the reason;
- distinguish a product or risk choice the user owns from a fact you can check;
- offer alternatives when the recommendation has a meaningful tradeoff.

Wait for the answers, update the decision map, then ask dependent questions.
Follow an answer's weakest assumption when it changes the plan. Before each
round, check the relevant dimensions below. Include independent decisions about
identity, shared resources, recovery and rollout when they matter; do not defer
them just to shorten the round.

## One-response mode

When asked for a complete pressure test in one response, identify the main
assumptions, concrete failure modes and smallest experiments that would
distinguish plausible outcomes.

Cover the relevant outcome, users, constraints, ownership, data model, failure
modes, security, operability, migration, rollback, cost and exclusions. Use
read-only evidence to resolve factual questions. Delegate only when permitted
and useful.

Keep confirmed decisions, unresolved risks and assumptions in a compact log.
Separate blockers from tolerable risks and reversible choices. Do not implement
the proposal or replace it with a preferred architecture unless requested.
Stop when the plan is ready to execute or the user asks to stop. Report the
decisions, remaining unknowns, focused experiments and first next step.

Before finishing, check for unresolved identity, authorization, observability,
recovery or rollout risks. Report relevant gaps without narrating every
irrelevant check.
