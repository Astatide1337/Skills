---
name: wizard
description: Design or implement a user-run setup wizard for configuration, credentials, or multi-step onboarding. Keep browser, secrets, and account changes under user control.
---

# Wizard

Create a project-native interactive script the user controls. When the
repository cannot support a portable script or the user requests design-only
guidance, give the procedure in the response; create a project runbook only
when the user explicitly requests that document. Do not run external account
setup end-to-end on their behalf.

1. Inspect the repository's existing setup, package manager, environment conventions, and documented prerequisites.
2. Derive the stages from real setup boundaries. For every input, record its
   source, destination, whether it is secret, validation rule, and safe
   completed-state check. Do not invent browser steps the provider does not
   require.
3. Map the interactive journey before implementing it. Show prerequisites,
   browser-owned actions, local inputs, previewed writes, verification, and
   disconnect or rollback.
4. Make every step resumable and idempotent. Detect completed work before changing it.
5. Validate inputs without echoing secrets. Use hidden input where supported and
   never pass secret values through command arguments, logs, or shell tracing.
   Restrict environment-variable names to safe identifiers.
6. Show exact target files, repositories, services, and accounts before writes.
7. Put secret values only in the platform or local secret store the project already uses. Never commit them.
8. Include verification after each boundary and a cleanup/recovery path for partial setup.
9. Leave external account mutation and credential entry visibly under user control unless they explicitly authorize execution.

For a shell wizard, use strict mode, quote expansions, detect required commands,
handle interruption, and support common Unix environments. Update environment
files by exact key without duplicating entries and preserve unrelated content.
Validate syntax and use the repository's shell linter when available. Exercise
a temporary test configuration without real secrets or account writes. Make
dry-run reject or replace live-looking credential values; its output must use
obvious fixed placeholders and must not echo any supplied secret or identifier.
Test missing dependencies as well as the happy path. Document the exact files
and keys removed by rollback, preserving unrelated configuration.

Prefer a short project-native script over a universal framework. Keep it
ephemeral unless repeated setup justifies committing it. Explain how to resume,
rerun, and remove what it created.
