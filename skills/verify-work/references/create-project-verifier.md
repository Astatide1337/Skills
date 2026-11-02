# Create a project verifier

Use this when the user asks for a reusable way to verify one application's user
behavior. Produce a feature map owned by the application and a short
`.agents/skills/verify-<app>/SKILL.md` that a new agent can follow.

## Interview the application

Trace one user entry point through the source. Find the launch command,
readiness signal, data and authentication prerequisites, existing browser or
CLI driver, observable result and safe test environment. Read the application's
types, schemas, lint and import rules, and CI. Keep those contracts in the
application rather than copying them into Skills.

Check whether an application CLI already supports the task. If so, install a
compatible version when setup is authorized and keep that version fixed for
the task. Do not copy its process or browser code into the skill. Otherwise,
use existing project tools for the requested work or identify the missing
capability. Another application's CLI is not a substitute.

## Write the app-owned map and skill

For each feature, the map must name:

- the real user journey and its sub-features;
- how the user reaches it and how the driver performs the actions;
- stable inputs or seeds and relevant prerequisites;
- the independently chosen expected result and a failure path;
- the evidence to retain.

Keep the map in the application when repository edits are authorized. Otherwise,
use an external user-owned profile as described in
[portable profiles](portable-profiles.md). Pin the CLI version in the app's
dependency lock or external verifier configuration, and reject unsupported
map/CLI combinations.

Do not store the application's own HEAD in the committed map. Derive a clean
app HEAD at startup, store it in the run manifest, and compare it before and
after exercising the feature. Candidate output cannot define its expected
value or remove a required check. Create only the requested feature files;
do not add a project README or general product document.

The skill must state:

1. **Trigger and outcome:** when to use it and which user-visible result it
   can verify.
2. **Launch and doctor:** exact startup and readiness commands, plus checks
   for instance identity, app revision, CLI version and authentication/data mode.
3. **Seed/reset:** isolated test data or stateless input, with resets limited
   to state created for this run.
4. **Drive:** exact app actions and named scenarios, using stable semantic
   selectors and the existing Playwright or agent-browser tools beneath any adapter.
5. **Assertions and evidence:** required checks, expected values from the
   app-owned map, screenshots, responses and side effects tied to the revision
   and instance. Explain JSON and exit codes. Distinguish accepted, failed,
   skipped and not-run checks.
6. **Recovery and cleanup:** inspect uncertain writes before retrying, retain
   user drafts on conflict, stop only owned processes and preserve evidence.

Show how to invoke every bundled helper, and make it executable. A reader
should not need to reverse-engineer it.

Check what a dry run contacts or changes before using it. If the baseline
cannot launch, repair a recoverable setup fault within scope or report the
exact blocker. Do not document a broken command as working.

## Prove the cold-reader recipe

From a fresh context, follow the written launch, doctor and seed steps. Exercise
one mapped real journey and a meaningful negative case, then clean up. Inspect
the result and confirm that the evidence survives cleanup.

Force one check to fail. Confirm a nonzero exit, a retained failure artifact
and cleanup of only the owned instance. Fix the instructions and repeat the
procedure. A unit test or mock alone does not establish application integration.
