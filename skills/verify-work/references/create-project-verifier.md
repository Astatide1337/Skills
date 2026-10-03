# Create a project verifier

Use this when the user asks for a reusable way to prove one application's user behavior. The result is an application-owned feature map and a short .agents/skills/verify-<app>/SKILL.md that a new agent can execute without guessing.

## Interview the application

Trace one user entry point through source and identify its launch command, readiness signal, data/auth prerequisites, existing browser or CLI driver, observable result, and safe isolation. Read the application's types, schemas, lint/import boundaries, and CI rather than moving those contracts into the shared Skills repository. Check whether a separate per-app executable CLI already supports this application. If it does, consume an exact version pinned by the application; do not copy its process or browser code into the skill. If it does not, use existing project tooling for the requested scope or report the missing capability. A CLI for another app is not a substitute.

## Write the app-owned map and skill

The feature map names a real user journey, stable input or seed, independently chosen expected result, failure path, and evidence to retain. Commit the map in the application repository. Pin the CLI version in the application's dependency lock or verifier configuration, and reject unsupported map/CLI versions. Do not pin the application's own HEAD inside that map: derive a clean app HEAD at startup, store it in the run manifest, and check it again before and after the drive. A candidate's output cannot supply its own expected value or remove a required check.
For each feature, record its sub-features, how a user reaches it, how the
driver acts, the observable end state, and relevant prerequisites. Start with
only the requested feature files. Do not add a project README or general
product document.

The skill must state:

1. **Trigger and outcome:** when to invoke it and which user-visible result it can prove.
2. **Launch and doctor:** exact owned startup/readiness command and how instance identity, app revision, CLI version, and auth/data mode are checked.
3. **Seed/reset:** isolated test data or stateless input, plus a reset that touches only run-owned state.
4. **Drive:** exact app actions and named scenarios, using stable semantic selectors and the existing Playwright or agent-browser stack beneath any adapter.
5. **Assertions and evidence:** required checks, expected values from the app-owned map, screenshots/responses/side effects with revision and instance identity, and reliable JSON/exit-code interpretation. Distinguish accepted, failed, skipped, and not-run checks.
6. **Recovery and cleanup:** inspect an uncertain write before retry; retain user drafts on conflict; stop only owned processes and preserve evidence after cleanup.

Show the invocation of every bundled helper in the skill and make it
executable; a reader should not have to reverse-engineer the helper.

Use dry-run only after observing whether it contacts or changes anything. If the baseline cannot launch, repair a recoverable in-scope setup fault or report the exact blocker. Do not document a broken command as working.

## Prove the cold-reader recipe

Execute the written launch, doctor, seed, one mapped real journey, a meaningful negative control, and cleanup from a fresh context. Inspect the captured result and verify the evidence remains after cleanup. Force one failed check and confirm a nonzero exit, a retained failure artifact, and cleanup of only the owned instance. Correct the instructions and run them again; a unit test or mock alone is not application integration evidence.
