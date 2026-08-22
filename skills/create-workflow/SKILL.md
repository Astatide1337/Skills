---
name: create-workflow
description: "Create or simplify a repeatable repository workflow by converting a recurring, bounded decision into the smallest deterministic artifact. Use when setup, release, maintenance, review, or repair depends on remembering steps, interpreting routine state, or repeatedly making the same choice. Do not use for a one-off procedure or to add project documentation unprompted."
---

# Create Workflow

Make the normal path explicit, replayable, and boring. The goal is not maximum automation; it is removing repeated judgment without creating a larger operational burden.

## Lock the acceptance contract

Before choosing an implementation, copy every literal deliverable from the
request into a short checklist: exact output paths, filenames, command names,
inputs, allowed changes, and required checks. These are constraints, not naming
suggestions. Verify each literal against the final workspace before reporting;
if one is absent, the workflow is not complete.

## Modes

- **Create:** capture a recurring manual or agent-run procedure as a repository-owned workflow.
- **Simplify:** reduce an existing workflow while preserving its guarantees, evidence, and recovery behavior.

In either mode, observe the real procedure before designing its replacement.

Classify the target before acting:

- **Repository-local:** developer setup, generation, validation, formatting, or maintenance owned by this checkout.
- **Delivery:** CI, release, migration, promotion, or deployment orchestration crossing environment boundaries.
- **Agent operation:** a recurring research, review, triage, or repair procedure whose useful decisions can be bounded by evidence.

Read `references/artifact-selection.md` when choosing the implementation form. Use `references/workflow-spec.md` to specify a non-trivial workflow before implementing it.

Inspect only the supplied repository and explicitly named inputs. Do not search
parent directories, `/tmp`, evaluator/grader paths, or unrelated repositories
for a workflow artifact. If the workflow cannot be observed from the supplied
evidence, return a bounded template with the missing inputs and stop; do not
invent paths, endpoints, digests, owners, or successful writes.

## Workflow

1. Observe only enough of the current procedure to name the repeated decision,
   declared inputs, desired output, and required failure. Do not expand a small
   check into a general policy engine.
2. Choose the smallest artifact that removes that decision: existing config,
   declarative config, schema, validator, idempotent script, platform
   orchestration, then service—in that order.
3. Preserve the requested interface exactly. Treat an explicit path, filename,
   command name, input format, and exit-code contract as acceptance criteria;
   do not substitute a clearer name or a different integration point without
   asking. Re-read these literals before writing and again before reporting.
4. Implement only the checks required by the repeated mistake and supplied
   input contract. Do not add duplicate detection, alternate formats, discovery,
   mutation, dry-run machinery, retries, or extensibility unless the task needs
   them. Every extra branch needs its own justification and test.
5. Make reruns safe and output stable. Prefer simple set operations and explicit
   sorting over stateful parsing. Never read secret values when names suffice.
6. Verify the current fixture, one focused success case, the required failure,
   and a rerun. Use temporary copies for alternate cases; do not rewrite the
   repository's source fixtures merely to exercise the validator.
7. Remove a superseded procedure only when the request identifies one and its
   ownership is clear.

## Refuse automation when it is worse

When the procedure is rare, judgment is genuinely contextual, the inputs cannot
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
- Can an untrusted input cause arbitrary command execution, URL access, data export, or deletion?
- What is the smallest test that proves normal operation no longer requires an agent?
- Who owns the workflow, and what event should cause it to be revised or deleted?

## Output

For planning, return a decision table with `repeated step`, `exported artifact`, `input contract`, `owner`, `failure behavior`, and `verification command`.

For implementation, create the smallest repository-native artifact and report
the exact commands and observed results for the focused checks above. Apply
clean-checkout, dry-run, rollback, retry, and side-effect gates only when the
workflow actually writes state, crosses environments, or performs delivery;
do not force production ceremony onto a read-only local validator.

Delete wrappers, duplicate configuration, speculative integrations, and runtime inference. Leave unresolved provider behavior blocked rather than encoding a guess.

## Execution boundary

Match the task's requested mode and the tools it authorizes.

- For prompt-only tasks that explicitly forbid workspace or tool use, use only
  the supplied text. `Review-only`, `diagnose`, and `do not edit` prohibit
  mutation, not observation: inspect in-scope supplied files with read-only
  tools unless the user also forbids that inspection. If required evidence is
  absent after checking the declared scope, identify the smallest artifact needed.
- For workspace-write requests, read only declared inputs and write only the declared output paths. Do not broaden the scope, probe credentials, inspect evaluator or harness metadata, or use network/MCP unless the task explicitly authorizes it.
- Never claim that a command, file change, deployment, or verification happened unless it actually happened and is supported by observed evidence.
