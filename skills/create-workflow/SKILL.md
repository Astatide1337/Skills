---
name: create-workflow
description: "Use when asked to automate or simplify a recurring manual or agent procedure. Not for one-off tasks."
---

# Create Workflow

Automate a repeated decision only when the result is easier to run and maintain
than the current procedure.

## Lock the acceptance contract

Before choosing an implementation, record the requested output paths, filenames,
commands, inputs, allowed changes and required checks. Preserve these exact
interfaces. Check them against the final workspace before reporting completion.

## Modes

- **Create:** capture a recurring manual or agent-run procedure as a repository-owned workflow.
- **Simplify:** reduce an existing workflow while preserving its guarantees,
  evidence, and recovery behavior.

Use only for explicitly requested recurring automation or simplification of an
existing workflow. A one-off investigation or test campaign does not imply a
permanent harness, CI job or reusable package. For native operation discovery,
use [tool contracts](../skill-creator/references/tool-contracts.md) and the owning
application's help; this skill does not wrap established CLIs.

In either mode, observe the real procedure before designing its replacement.

Classify the target before acting:

- **Repository-local:** developer setup, generation, validation, formatting, or
  maintenance owned by this checkout.
- **Delivery:** CI, release, migration, promotion, or deployment orchestration
  crossing environment boundaries.
- **Agent operation:** a recurring research, review, triage, or repair procedure
  whose useful decisions can be bounded by evidence.

Read `references/artifact-selection.md` when choosing the implementation form.
Use `references/workflow-spec.md` to specify a non-trivial workflow before
implementing it.

Inspect only the supplied repository and explicitly named inputs. Do not search
parent directories, `/tmp`, evaluator/grader paths, or unrelated repositories
for a workflow artifact. If the workflow cannot be observed from the supplied
evidence, return a bounded template with the missing inputs and stop; do not
invent paths, endpoints, digests, owners, or successful writes.

## Workflow

1. Observe the current procedure. Identify the repeated decision, its inputs
   and output, and the invalid case it must reject. Do not expand a small
   check into a general policy engine.
2. Choose the smallest artifact that removes that decision: existing config,
   declarative config, schema, validator, idempotent script, platform
   orchestration, then service—in that order.
3. Preserve the requested interface, including input formats and exit codes.
   Ask before substituting a name, path or integration point.
4. Implement only the checks required by the repeated mistake and supplied
   input contract. Do not add duplicate detection, alternate formats, discovery,
   mutation, dry-run machinery, retries, or extensibility unless the task needs
   them. Add a branch only for a stated requirement and test the behavior it adds.
5. Make reruns safe and output stable. Prefer simple set operations and explicit
   sorting over stateful parsing. Never read secret values when names suffice.
6. Verify the current fixture, one focused success case, the required failure,
   and a rerun. Use temporary copies for alternate cases; do not rewrite the
   repository's source fixtures merely to exercise the validator.
7. Remove a superseded procedure only when the request identifies one and its
   ownership is clear.

## Refuse automation when it is worse

When the procedure is rare, the decision depends on context, the inputs cannot
be validated, or automation would introduce disproportionate credentials,
state, mutation, or maintenance cost, recommend a one-off procedure in the
response rather than automating it. Write it into repository documentation only
when the user requests a project document or names the destination.

When the artifact carries a digest, bind every digest to an explicit relative
path or immutable artifact identity. A syntax-valid digest is not evidence: the
validator must read the referenced bytes, compute the digest, and compare the
values. Reject an artifact that contains a digest with no verifiable target.

## Audit questions

- What decision is being made repeatedly, and what exact fact would make it deterministic?
- Is this file executable, or is it only documenting a command that should be documented once?
- Does the proposed automation add state, credentials, retries, or an operator surface?
- Can an untrusted input cause arbitrary command execution, URL access, data
  export, or deletion?
- What is the smallest test that proves normal operation no longer requires an agent?
- Who owns the workflow, and what event should cause it to be revised or deleted?

## Output

For planning, explain the repeated decision, proposed artifact, inputs, owner,
failure behavior, and verification needed for this workflow. Use the planning
format in [plans and authority](../follow-instructions/references/approved-plans.md);
choose a table only when it makes the decision easier to compare.

For implementation, create the smallest repository-native artifact and report
the exact commands and observed results for the focused checks above. Apply
clean-checkout, dry-run, rollback, retry, and side-effect gates only when the
workflow actually writes state, crosses environments, or performs delivery;
a read-only local validator does not need these operational checks.

Remove unnecessary wrappers, duplicate configuration and speculative integrations
added by this task. If provider behavior is unknown, inspect its documented
contract or report the unresolved dependency; do not encode a guess.

## Execution boundary

Apply the shared [execution
boundary](../follow-instructions/references/principles/authority-and-claims.md#execution-boundary).
Keep the task-specific restrictions above; this skill grants no additional
effects.
