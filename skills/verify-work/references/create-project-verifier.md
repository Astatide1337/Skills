# Create a project verifier

Create a repository-specific skill that lets a future agent prove behavior through the same surface a user touches.

## Interview the repository

Infer these from source and ask only for what cannot be observed:

- **Surface:** web UI, CLI/TUI, desktop, mobile, API, service, or library.
- **Launch:** project-native command, prerequisites, ports, environment, seed data, and authentication.
- **Drive:** existing Playwright/Cypress tests, PTY helpers, request scripts, debug protocols, or other harnesses. Prefer existing machinery.
- **Observe:** screenshots, recordings, transcripts, responses, logs, exit codes, files, database state, or emitted messages.
- **Isolate:** ports, profiles, data directories, and whether concurrent instances are safe.

Do not document a broken baseline as a working procedure. Fix an in-scope startup problem first or report the blocker precisely.

## Generate `.agents/skills/verify-<app>/`

Create a concise `SKILL.md` with valid `name` and `description`, plus these grounded sections:

1. **Launch:** exact start/readiness/teardown procedure. Short-lived programs get an isolated session per drive.
2. **Doctor:** a read-only check that confirms the intended instance, build/version, port, and authentication are usable.
3. **Drive:** real commands or stable semantic selectors from this repository. Avoid coordinates and tab order.
4. **Evidence:** capture both action and result. Verify visible state and material side effects. Name the artifact location.
5. **Cleanup:** stop only processes created by the run and remove only its scratch state. Preserve evidence.
6. **Helpers:** document every bundled helper invocation and make scripts executable.

Never trust a `dry-run` label without observing what it still changes or contacts.

## Seed the feature map

Create only the feature-map files needed for the verifier scope the user asked
for. Do not add a project README or general product documentation. Keep a
compact index in the verifier's `SKILL.md`; add a feature file only when its
launch, drive, or evidence recipe cannot stay clear there. Each feature records:

- sub-features;
- how a user reaches it;
- how the harness drives it;
- the observable end state that proves it works;
- prerequisites and gotchas.

## Prove the verifier

Run launch, doctor, one mapped feature, evidence capture, and cleanup end to end. Confirm the evidence survives cleanup. Clean residue after failed attempts. A verifier that has not executed its own instructions is a draft, not verified infrastructure.
