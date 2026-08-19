---
name: wizard
description: Design a user-run setup wizard for configuration, credentials, or multi-step project onboarding. Use when setup needs human input, browser steps, local environment changes, or external secrets and should be repeatable without letting the agent silently mutate accounts.
---

# Wizard

Create a script or runbook the user controls. Do not run an interactive setup end-to-end on their behalf.

1. Inspect the repository's existing setup, package manager, environment conventions, and documented prerequisites.
2. List required inputs and classify them as public configuration, secret, or external account action.
3. Make every step resumable and idempotent. Detect completed work before changing it.
4. Validate inputs without echoing secrets. Restrict environment-variable names to safe identifiers.
5. Show exact target files, repositories, services, and accounts before writes.
6. Put secret values only in the platform or local secret store the project already uses. Never commit them.
7. Include verification after each boundary and a cleanup/recovery path for partial setup.
8. Leave the final external mutation or credential entry visibly under user control unless they explicitly authorize execution.

Prefer a short project-native script over a universal framework. Explain how to resume, rerun, and remove what it created.
