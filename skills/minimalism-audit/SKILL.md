---
name: minimalism-audit
description: "Convert a repeated reasoning-heavy workflow into the smallest deterministic repository artifact: configuration, schema, validation, script, or automation. Use when normal operation still depends on an agent remembering steps, making choices, or repairing predictable state."
---

# Minimalism audit

The goal is not more automation. The goal is to make the normal path explicit, replayable, and boring.

Inspect only the supplied repository and explicitly named inputs. Do not search
parent directories, `/tmp`, evaluator/grader paths, or unrelated repositories
for a workflow artifact. If the workflow cannot be observed from the supplied
evidence, return a bounded template with the missing inputs and stop; do not
invent paths, endpoints, digests, owners, or successful writes.

## Workflow

1. Observe the workflow from a fresh checkout. Record every human or agent decision, input, output, side effect, retry, and failure branch.
2. Separate invariants from choices. An invariant belongs in configuration or a schema; a bounded check belongs in validation; a repeatable transformation belongs in a script; orchestration belongs in the platform only when the platform already owns it.
3. Export the smallest artifact that removes each repeated decision, in this order: existing platform configuration, declarative config, schema, validation, idempotent script, then a service. Do not add a service to replace one command.
4. Make inputs explicit and allow-listed. Fail closed on missing, unknown, malformed, or ambiguous values. Never infer credentials, endpoints, scopes, paths, or destructive targets.
5. Make reruns safe. Use stable paths, deterministic ordering, explicit timeouts, bounded retries, dry-run support for writes, and no hidden network or filesystem discovery.
6. Keep secrets outside the artifact. Accept them only through the platform’s runtime secret mechanism; never generate, persist, log, or echo them.
7. Add a verification path that starts from a clean checkout and proves the artifact’s output, failure behavior, and absence of unintended side effects.

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

## Output

Return a decision table with `repeated step`, `exported artifact`, `input contract`, `owner`, `failure behavior`, and `verification command`. Delete wrappers, duplicate configuration, speculative integrations, and runtime inference. Leave unresolved provider behavior explicitly blocked rather than encoding a guess.

## Execution boundary

Match the task's requested mode and the tools it authorizes.

- For text-only, plan-only, or review-only requests, use the supplied prompt and explicitly provided context. Do not inspect the workspace, run shell/CLI commands, call network/MCP/browser tools, or edit files. If required context is missing, say so and identify the smallest artifact needed.
- For workspace-write requests, read only declared inputs and write only the declared output paths. Do not broaden the scope, probe credentials, inspect evaluator or harness metadata, or use network/MCP unless the task explicitly authorizes it.
- Never claim that a command, file change, deployment, or verification happened unless it actually happened and is supported by observed evidence.
