# Implement / bug, feature, refactor

## When

Use for an authorized repository change. A clear local correction uses the router's default path. Add debugging, architecture, UI, security, or review guidance only for a material decision.

## Inputs to establish

- Expected behavior, affected owner/callers, existing checks, and relevant environment.
- Requested scope, compatibility, permitted delivery, and unrelated dirty work.

## Steps and decision points

1. Inspect the actual owner and establish the expected outcome. Try the original bug reproducer when available; features and refactors use their observable contract.
2. Resolve causal or ownership uncertainty with the smallest useful check. Do not invent multiple hypotheses or alternative designs for a clear correction.
3. Build a complete slice using existing capability. For substantial work, exercise the representative full path early before expanding variants.
4. Run affected project checks and actual API/CLI/browser actions. Review correctness and minimalism; deeper structural and independent review follow the [risk triggers](../references/principles/authority-and-claims.md#review-risk-triggers).
5. Address actionable findings, rerun affected checks, and complete authorized commit/push or [PR work](../../pull-requests/SKILL.md). Never infer merge or deploy permission.

## Failure and recovery

Repair recoverable prerequisites. If the original pre-change comparison cannot run, use supported alternative evidence and state its limits. A failure changes the hypothesis, not the acceptance. Revise internal choices and continue; ask only about material changes beyond existing authorization. Repeated failure uses [recovery](../../self-reflect/SKILL.md).

## Completion evidence

Report changed behavior, relevant checks, final diff scope, and material gaps. Local verification and remote readiness are separate. A build alone is not a user journey.

## Example

Fix a tenant lookup, exercise allowed and denied requests, preserve the cross-tenant regression, and obtain independent security review.

## Near-miss

A behavior-preserving refactor does not authorize a new feature or validation policy.
