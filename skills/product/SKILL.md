---
name: product
description: "Use when defining a feature's users, problem, scope or acceptance, prioritizing product work, or challenging whether a proposal solves the right problem."
---

# Product

Resolve what should change for the user before choosing how to build it. Use
existing requirements, issues, feedback and the actual product. A clear bug fix,
visual styling task or settled technical design needs no product discovery.

## Establish the need

Identify the user, the task they are trying to finish, the present obstacle and
the observable result they need. Inspect the current journey and comparable
features before assuming a capability is missing. Distinguish observed demand
from a hypothesis; do not invent customer research, personas or impact numbers.

Check whether a smaller change to the existing flow would solve the problem.
Recommend doing nothing when the supposed problem is unsupported, while stating
what evidence would change that decision. Do not silently drop requested work.

## Choose the scope

Define the smallest complete user journey: entry point, necessary input, useful
result and relevant failure or recovery behavior. Include empty, denied or
interrupted states when they affect that journey. A collection of components is
not a usable feature.

Keep explicit requirements. Separate essential behavior from optional polish and
future possibilities; do not add speculative features to make a proposal sound
ambitious. For prioritization, compare user benefit, evidence, dependencies,
cost and risk without manufacturing precision. Explain the recommendation and
the tradeoff that could change it.

## Challenge the proposal

Before presenting it, test its weakest premise: does the proposed change remove
the user's obstacle, can existing behavior already do so, and what could make the
result unusable? Resolve factual questions from available sources or a small
authorized experiment. Ask only for a consequential preference or business
constraint that cannot be inferred safely. Give a recommendation and explain
what depends on the answer. Batch independent questions; do not make the user
conduct the investigation through repeated approvals.

A request to critique or pressure-test an idea stays read-only. An implementation
request continues within its existing authority after these decisions; this
skill creates no additional approval gate.

## Carry the decision into implementation

Keep a compact statement in the existing task record or requested deliverable:
user and problem, chosen scope and reason, exclusions, observable acceptance,
and any decision that still needs the user. Write a PRD only when requested or
required by the repository; do not create a parallel documentation tree.

Acceptance describes what the user can do and what must remain true, including
one relevant counterexample. Choose evidence for that behavior before editing.
Use [planning](../follow-instructions/references/approved-plans.md) for the
implementation decision, [architect](../architect/SKILL.md) for uncertain code
boundaries and [web-interface](../web-interface/SKILL.md) for interaction design.
During delivery, compare the working journey with this acceptance; passing
component checks alone does not establish the product outcome.
