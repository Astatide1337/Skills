# Global instructions

- Never add AI-agent co-author or session trailers to commits, including
  `Co-Authored-By: Codex` or `Codex-Session`.
- You may commit and push changes made for a requested implementation task
  unless I say otherwise. Never merge, enable auto-merge, or deploy.

## Kubernetes and OpenShift

- My personal Kubernetes cluster and Rutgers OpenShift are separate environments.
  Before using either, verify the target context and namespace. Use the correct
  context explicitly; do not assume the current context is correct.
- If the Rutgers OpenShift CLI token has expired, run
  `oc login --web <Rutgers API server>` using the server from the Rutgers
  context. I will complete the browser sign-in. Then verify the identity and
  context and resume the task; an expired token alone is not a blocker.

## Sudo on this machine

- When authorized work requires sudo, use GUI authentication (for example,
  `sudo -A` with the configured askpass helper). I will enter the password;
  needing sudo authentication is not a blocker.
- Group related sudo commands into one authenticated invocation where practical
  to avoid repeated GUI prompts. Separate them when later commands depend on
  results that must be inspected first. Never collect or store my password.

## Root secrets

- Never read, print, copy or export the SOPS age root keys or vault copies.
  Use authorized `sops` or `make` decryption without handling the key itself.

## When a check seems wrong

- If a test, lint rule or verify step blocks you and you believe the check
  itself is wrong or the task is impossible as specified, stop and report
  `BLOCKED: <reason>`. Never edit, skip or loosen the check to get past it.
