---
name: create-workflow
description: "Create or simplify a repeatable repository workflow by converting recurring human or agent decisions into the smallest deterministic artifact: existing configuration, declarative config, schema, validation, idempotent script, or platform automation. Use when setup, release, maintenance, review, or repair still depends on remembering steps, interpreting routine state, or repeatedly making the same bounded choices."
---

# Create Workflow

Make the normal path explicit, replayable, and boring. The goal is not maximum automation; it is removing repeated judgment without creating a larger operational burden.

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

1. Observe the workflow from a fresh checkout. Record every human or agent decision, input, output, side effect, retry, and failure branch.
2. Separate invariants from choices. An invariant belongs in configuration or a schema; a bounded check belongs in validation; a repeatable transformation belongs in a script; orchestration belongs in the platform only when the platform already owns it.
3. Export the smallest artifact that removes each repeated decision, in this order: existing platform capability, declarative config, schema, validation, idempotent script, CI or task-runner orchestration, then a service. Do not add a service to replace one command.
4. Make inputs explicit and allow-listed. Fail closed on missing, unknown, malformed, or ambiguous values. Never infer credentials, endpoints, scopes, paths, or destructive targets.
5. Make reruns safe. Use stable paths, deterministic ordering, explicit timeouts, bounded retries, dry-run support for writes, and no hidden network or filesystem discovery.
6. Keep secrets outside the artifact. Accept them only through the platform’s runtime secret mechanism; never generate, persist, log, or echo them.
7. Add a verification path that starts from a clean checkout and proves the artifact’s output, failure behavior, and absence of unintended side effects.
8. Remove or supersede the old procedure so two sources of truth do not survive. Preserve a short human escape hatch only for failures the workflow cannot safely resolve.

## Refuse automation when it is worse

Prefer concise documentation when the procedure is rare, judgment is genuinely contextual, the inputs cannot be validated, or automation would introduce credentials, persistent state, external mutation, or maintenance cost disproportionate to the mistake it prevents. A valid result is “document this once; do not automate it,” with the reason and reconsideration trigger.

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

For implementation, create the smallest repository-native artifact, remove the superseded path, and run its clean-checkout, normal-path, failure-path, rerun, and side-effect checks. Report any remaining judgment as an explicit manual boundary.

Do not claim the workflow is ready until all five proof gates have current evidence:

1. **Bootstrap:** a clean checkout can discover and invoke it.
2. **Normal path:** valid inputs produce the declared artifact or state.
3. **Failure path:** missing, malformed, ambiguous, or disallowed inputs fail closed with a useful error.
4. **Rerun:** a second identical run is safe and produces no unexplained drift.
5. **Side effects:** observed filesystem, network, credentials, and external mutations match the declared contract.

Delete wrappers, duplicate configuration, speculative integrations, and runtime inference. Leave unresolved provider behavior blocked rather than encoding a guess.

## Execution boundary

Match the task's requested mode and the tools it authorizes.

- For text-only, plan-only, or review-only requests, use the supplied prompt and explicitly provided context. Do not inspect the workspace, run shell/CLI commands, call network/MCP/browser tools, or edit files. If required context is missing, say so and identify the smallest artifact needed.
- For workspace-write requests, read only declared inputs and write only the declared output paths. Do not broaden the scope, probe credentials, inspect evaluator or harness metadata, or use network/MCP unless the task explicitly authorizes it.
- Never claim that a command, file change, deployment, or verification happened unless it actually happened and is supported by observed evidence.
