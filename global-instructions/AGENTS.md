# Global instructions

- For non-trivial engineering work, start with the `follow-instructions` skill
  when it is installed; it picks the procedure and the domain skills to load.
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

## Personal context

- For who I am and cross-project decisions, read the [wiki decisions](https://github.com/Astatide1337/astatide-wiki/tree/main/content/decisions).
- Skills holds how to work; each repository's `AGENTS.md` holds that codebase.
- Keep mechanically enforceable invariants in types, lint, tests and CI.
