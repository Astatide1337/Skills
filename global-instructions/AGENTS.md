# Global instructions

- For non-trivial engineering work, start with the `follow-instructions` skill
  when it is installed; it picks the procedure and the domain skills to load.
- Never add AI-agent co-author or session trailers to commits, including
  `Co-Authored-By: Codex` or `Codex-Session`.
- Implementation requests normally include committing, pushing and opening a
  scoped PR unless I request local-only work or set another restriction.
  For planning, explanation or review, perform only the requested actions.
  Merge only after I explicitly approve that merge.
  Never enable auto-merge. Prepare and verify the deployment before asking for
  my final approval. Deploy only after I explicitly approve that deployment.
- An issue URL sent as a work item means implementation through a verified
  PR/MR. Preserve explicit read-only requests and repository-specific write rules.
- Keep one-off plans, research, investigation notes and verification reports
  outside project checkouts. Add maintained Markdown only when requested or
  needed to use or operate the changed behavior; update existing docs first.
- Present substantial implementation plans as standalone HTML unless I request
  another format. Keep working notes separate from the plan I review.

## Personal context

- I primarily work in T3 Code. Prefer Codex Cloud or my native agent-work
  libvirt VM, kagent (`kagent-vm` on `sohim`), when tools, repository access and
  runtime support the task; state when execution falls back to the laptop.
  kagent means this VM, not the kagent.dev Kubernetes framework. See Fleet's
  [machine record](https://github.com/Astatide1337/fleet/blob/main/machines/kagent.md)
  for operations. OpenBot means [nightly-labs/openbot](https://github.com/nightly-labs/openbot).
- When I say “fleet”, read the [Fleet repository](https://github.com/Astatide1337/fleet)
  README, operations guide and relevant machine records before choosing targets
  or procedures. Verify recorded state on the target; Fleet provides context,
  not additional authority.

- For who I am and cross-project decisions, read the [wiki decisions](https://github.com/Astatide1337/astatide-wiki/tree/main/content/decisions).
- Skills describes how to work; each repository's `AGENTS.md` supplies its local rules.
- Enforce rules in types, lint, tests or CI when those tools can check them.
- For delegated engineering work, select an available model and reasoning level
  suited to the role using `follow-instructions`' agent-selection policy. Honor
  explicit model, provider, effort and spending constraints. Keep parent-session
  and global settings unchanged; do not silently switch after a failed dispatch.

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
- When I explicitly authorize building or repairing an evaluator, changes to
  that evaluator are in scope. Preserve independent acceptance checks, validate
  the instrument against valid alternatives and targeted defects, and report
  changed measurements separately. This does not authorize weakening the
  underlying user outcome or an unrelated task gate.
