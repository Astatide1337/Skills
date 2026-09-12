# Engineering principles

This is a compact adaptation of the decision-oriented principles in Cursor's
pstack `poteto-mode`, pinned to commit
[`60c641e4`](https://github.com/cursor/plugins/tree/60c641e4fad674784b30abcf9f8915dea39df38d/pstack).
The summaries below are local guidance, not a wholesale copy of pstack's
model, tools, or autonomy rules. Load a rule when its trigger is present.

## Solve the requested outcome

- **Trigger:** The request is broad, or a new dependency or service is being
  considered.
- **Decision rule:** Define the observable result and literal non-goals. Inspect
  existing capabilities before adding moving parts.
- **Example:** A pagination omission earns a focused domain correction, not a
  second persistence subsystem.
- **Limit:** Identify real dependencies and do not pretend a coupled system is
  isolated.
- **Owners:** `create-workflow`, `architect`.

## Establish state and ownership first

- **Trigger:** Shared behavior, a new interface, or state crossing a process or
  module boundary is changing.
- **Decision rule:** Find the authoritative state, callers, lifetime, writers,
  and contract before editing the owner.
- **Example:** Fix the pagination function used by the MCP handler instead of
  adding a transport-only workaround.
- **Limit:** A clear local correction does not need competing architecture
  documents or new types everywhere.
- **Owners:** `architect`, `how`, `production-safety` when operational state is
  involved.

## Prefer the simplest sufficient design

- **Trigger:** An abstraction, adapter, helper, dependency, or cleanup is
  tempting.
- **Decision rule:** Reuse an existing interface and remove unnecessary layers
  before adding one. Keep responsibility with its current owner.
- **Example:** Reuse the project's database client and test runner rather than
  writing a generic pagination library.
- **Limit:** Fewer lines are not better when they hide ownership, weaken
  correctness, or make the next change harder.
- **Owners:** `create-workflow`, `code-review-and-quality`.

## Investigate causes and test behavior

- **Trigger:** A bug, regression, unexplained result, or conflicting report is
  present.
- **Decision rule:** Preserve a reproducer, state competing explanations when
  uncertainty is material, and run the smallest check that distinguishes them.
  Keep source facts separate from inference.
- **Example:** Run the original pagination traversal and inspect the cursor
  owner before changing the query.
- **Limit:** A missing baseline stays an explicit limitation; it never justifies
  invented before-and-after evidence.
- **Owners:** `systematic-debugging`, `verify-work`.

## Optimize user and maintainer experience

- **Trigger:** Scope, interface, error handling, documentation, or a UI state
  affects someone using or maintaining the result.
- **Decision rule:** Choose a small coherent journey that a maintainer can trace,
  and exercise relevant loading, empty, error, keyboard, or accessibility states
  when they exist.
- **Example:** A form error points to the actual invalid field and moves focus
  there, rather than merely changing its color.
- **Limit:** A backend-only change does not require a browser session, and a
  polished screenshot does not prove runtime behavior.
- **Owners:** `web-interface`, `verify-work`, `teach`.

## Scale process to consequence and uncertainty

- **Trigger:** The task touches sensitive data, production-like state, external
  writes, multiple writers, or an unresolved design fork.
- **Decision rule:** Add only the inspection, rollback, review, recovery plan,
  and evidence needed for that consequence. Keep ordinary tasks direct.
- **Example:** An authorized `kubectl get` can inspect state without authorizing
  `kubectl apply`; a migration needs a rollback before mutation.
- **Limit:** Risk does not justify a mandatory report template or repeated
  permission question for every ordinary issue.
- **Owners:** `production-safety`, `security-and-hardening`, `pull-requests`.

## Separate independent work before parallelizing

- **Trigger:** Delegation or parallel work is proposed.
- **Decision rule:** Settle shared interfaces and split writers first. Give each
  worker a bounded outcome, source, authority, and evidence requirement, then
  inspect and integrate the returned artifact.
- **Example:** One worker owns the API contract and another owns a disjoint UI
  state only after the contract is fixed.
- **Limit:** No second agent is required for a small serial change, and green
  worker results are not integration proof.
- **Owners:** `parallel` playbook.

## Question a repeatedly failing approach

- **Trigger:** Related repairs keep producing new repairs or the same gate keeps
  failing.
- **Decision rule:** Identify the shared premise, test it against current
  evidence, and narrow or replace the approach before adding machinery.
- **Example:** If evaluator hardening consumes every milestone without improving
  an actual workflow, pause expansion and run one supervised repository task.
- **Limit:** Do not evade an unmet requirement by redefining success, and do not
  change global instructions during an unrelated application task.
- **Owners:** `grilling`, `create-workflow`.

## Make claims match evidence and authority

- **Trigger:** A task is about to be called complete or a draft/write/merge/
  deployment boundary is crossed.
- **Decision rule:** Verify the actual artifact and requested layer. Distinguish
  fixing, drafting, creating, publishing, merging, and deploying.
- **Example:** A green build supports a build claim; a browser or API journey is
  needed for a user-visible behavior claim.
- **Limit:** Do not infer comprehension, production health, or superiority from
  a proxy check or one successful run.
- **Owners:** `verify-work`, `pull-requests`, `production-safety`.
