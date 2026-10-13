# Planning and continuation

Use a plan when requested, when a substantial dependency sequence benefits from
one, or when consequential choices cannot be resolved from available evidence.
Implementation authorization does not depend on a formal HTML plan. Reuse the
user's existing approval and scope instead of repeatedly seeking confirmation.

## Make the decision reviewable

Inspect actual code and environment. State intended behavior, affected owners,
acceptance checks, relevant failure paths, unresolved choices, and a practical
sequence. Compare alternatives only when they represent real tradeoffs.
Use the requested medium; HTML or a clickable prototype can help assess a
decision, but is not a universal prerequisite. Do not create a permanent plan
artifact for a simple task unless requested.

Plan-only work stops before implementation. Where a decision really belongs to
the user, complete available research and a concrete recommendation before asking.
Otherwise proceed with reasonable reversible choices inside authorized scope.

## Continue the authorized result

Implement, verify, address relevant review findings, and complete permitted
commit/push or PR work. Independent review follows the
[risk triggers](principles/authority-and-claims.md#review-risk-triggers), not a
blanket nontrivial-feature rule. Preserve explicitly requested review gates.
Never merge, enable auto-merge, or deploy contrary to personal instructions.

If evidence changes an internal implementation choice, revise the working plan
and continue. Ask about a material change to requested behavior, external
interfaces, scope, or consequential effects that existing authorization does
not cover. A reviewer proposal is evidence, not new authority. Do not reopen an
approval cycle for behavior-preserving simplification.

Keep only continuation facts that matter: outcome, accepted decisions, remaining
work, source/artifact identity, checks and failures, next action, actual blockers.
Use existing task state or [checkpoints](durable-checkpoints.md) across interruption.
No approval database, mandatory digest, or separate runtime is needed.

## Evidence and limits

Use source, tests, and interactions appropriate to the claim. Repair recoverable
prerequisites; use supported equivalent checks and state what remains unproven.
Missing remote CI can leave local implementation verified while remote readiness
remains pending. Do not manufacture success, skip a failed required assertion,
or claim an unreturned independent review.
