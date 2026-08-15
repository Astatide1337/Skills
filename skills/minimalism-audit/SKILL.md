---
name: minimalism-audit
description: "Convert a repeated reasoning-heavy workflow into the smallest deterministic repository artifact: configuration, schema, validation, script, or automation. Use when normal operation still depends on an agent remembering steps, making choices, or repairing predictable state."
---

# Minimalism audit

The goal is not more automation. The goal is to make the normal path explicit, replayable, and boring.

## Workflow

1. Observe the workflow from a fresh checkout. Record every human or agent decision, input, output, side effect, retry, and failure branch.
2. Separate invariants from choices. An invariant belongs in configuration or a schema; a bounded check belongs in validation; a repeatable transformation belongs in a script; orchestration belongs in the platform only when the platform already owns it.
3. Export the smallest artifact that removes each repeated decision, in this order: existing platform configuration, declarative config, schema, validation, idempotent script, then a service. Do not add a service to replace one command.
4. Make inputs explicit and allow-listed. Fail closed on missing, unknown, malformed, or ambiguous values. Never infer credentials, endpoints, scopes, paths, or destructive targets.
5. Make reruns safe. Use stable paths, deterministic ordering, explicit timeouts, bounded retries, dry-run support for writes, and no hidden network or filesystem discovery.
6. Keep secrets outside the artifact. Accept them only through the platform’s runtime secret mechanism; never generate, persist, log, or echo them.
7. Add a verification path that starts from a clean checkout and proves the artifact’s output, failure behavior, and absence of unintended side effects.

## Audit questions

- What decision is being made repeatedly, and what exact fact would make it deterministic?
- Is this file executable, or is it only documenting a command that should be documented once?
- Does the proposed automation add state, credentials, retries, or an operator surface?
- Can an untrusted input cause arbitrary command execution, URL access, data export, or deletion?
- What is the smallest test that proves normal operation no longer requires an agent?

## Output

Return a decision table with `repeated step`, `exported artifact`, `input contract`, `owner`, `failure behavior`, and `verification command`. Delete wrappers, duplicate configuration, speculative integrations, and runtime inference. Leave unresolved provider behavior explicitly blocked rather than encoding a guess.
