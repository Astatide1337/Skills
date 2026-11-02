# Agent gates

Hooks and a CI check that make an agent's "done" depend on checks it did not
write. Skills describe good work; these make the common shortcuts fail
loudly.

They exist because of failures that kept happening in real sessions:

- Work was reported complete while integration tests were skipped and
  fixtures were synthetic.
- Verification happened only when the user asked for it again ("verify that
  T1 is complete", "check the git diff", "do better testing").
- Weakening a test, a lint rule or a hook is the easiest way for an agent to
  turn a red check green, and nothing stopped it.

## What runs

| Piece | When | Effect |
|---|---|---|
| `agent_gates.py session-start` | Session start | Snapshots the repository's working tree, including uncommitted and untracked files. |
| `agent_gates.py guard` | Before `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | Snapshots any other repository the tool is about to touch. Refuses `--no-verify`, `git commit -n`, `HUSKY=0`, `SKIP=…`, `core.hooksPath` changes, and edits to the gate's state or Claude Code's hook settings. |
| `agent_gates.py format` | After `Edit`, `Write`, `MultiEdit` | Formats the file with the project's own Biome, Prettier, Ruff or gofmt, when the project configures one. Never runs a binary committed to the repository. |
| `agent_gates.py stop` | Before the agent stops | For every repository that changed this session, runs the integrity check and the verify command. Blocks the stop on a failure. |
| `test_integrity.py` | Locally or in CI | Fails on removed tests, new skip/only/todo markers in existing tests, and edits to lint, type, test-runner or verify configuration. Reports workflow edits without failing. |
| `.github/workflows/test-integrity.yml` | Pull requests in application repositories | Runs the integrity check against the base branch. A human approves an intentional change with a label. |

### The stop gate

- **Only checks what this session changed.** A repository counts as changed when its working tree differs from the session-start snapshot. A read-only session is never verified, even in a dirty repository, and edits you made before the session are never blamed on the agent.
- **Checks every repository the session touched.** That covers the session's own repository, any repository an edit or command reached, and git worktrees created during the session. If no snapshot exists (for example, the state was lost), it compares against `HEAD` at the session's start from the reflog, then the upstream branch, and says so.
- **Finds the verify command** from, in order: `AGENT_VERIFY_CMD`; a `verify` script in `package.json`, run with the lockfile's package manager; or a `verify:` target in a `Makefile` or `justfile`. A repository without one still gets the integrity check.
- **Runs verify only on trusted paths.** It runs only under `AGENT_GATES_TRUSTED` (paths separated by `:`, defaulting to your home directory). Elsewhere it notifies you instead of running. It also notifies instead of blocking when the runner (`just`, `pnpm` and so on) is not installed.
- **On failure,** the agent sees the last 80 lines of output and is told to fix the cause, not the check. Each turn gets 3 attempts. After that the agent may stop, with a notice that the work is unverified, and that unchanged tree is not verified again. A new turn starts fresh.
- **Avoids rerunning.** A passing tree is remembered, including any report files verify writes, so stopping again without changes does not rerun verify. A timed-out verify has its whole process group stopped.
- **Integrity findings** appear even while verify fails. A finding blocks once and asks the agent to restore the check, or to name each item if you asked for the change. After that you get a notice on every stop instead, so you always see it. An approved finding does not block again when unrelated files change.
- **Internal errors** produce a "this stop was not checked" notice rather than passing silently.

State lives in `${XDG_STATE_HOME:-~/.local/state}/agent-gates/`; override it with `AGENT_GATES_STATE`. `AGENT_VERIFY_TIMEOUT` defaults to 540 seconds.

## Install (Claude Code)

Installing is an explicit, per-machine choice, like `global-instructions/AGENTS.md`:

1. Copy the `hooks` block from `claude-settings.example.json` into `~/.claude/settings.json`, or into one project's `.claude/settings.json` to try it there first.
2. Replace `$SKILLS_DIR` with the absolute path of this checkout.
3. Optionally set `AGENT_GATES_TRUSTED` to the directories whose verify commands may run.
4. Run `/hooks` in Claude Code and confirm all four are listed.

Requires `python3` 3.11+ and `git` on `PATH`. Nothing else.

## Opt-in task completion hook (Codex prototype)

The existing `stop` check verifies changed code. It cannot detect a missing
deliverable when the agent changed nothing. The separate `completion` command
runs a task-specific acceptance check on every `Stop`, without relying on
changes or the assistant's final wording:

```sh
python3 agent_gates.py completion python3 /trusted/task_acceptance.py < hook-input.json
```

The checker must be explicitly selected and reviewed for the actual task. Keep
it outside the agent's writable workspace; hook trust covers the hook definition,
not the contents of every script it calls. Do not let the assistant generate its
own acceptance oracle and then treat it as independent. The hook never takes a
command from the event payload, final reply or transcript.

The command runs in the event's working directory, without a shell. It must
exit zero and print exactly one JSON object with `status` and a nonempty `reason`.
Do not print credentials or other diagnostics into this output.

| Checker status | Hook behavior |
| --- | --- |
| `complete` | Allows stopping. The checker is responsible for proving the actual task outcome. |
| `incomplete` | Returns `decision: block` and the reason, requesting another native continuation. |
| `blocked`, `waiting`, `cancelled` | Allows stopping with an explicit **not complete** notice. The checker must establish the real authority/dependency, live wait or cancellation; assistant narration is not evidence. |
| Invalid output, nonzero exit, timeout | Reports an unavailable check and requests recovery; never counts as acceptance. |

It requests at most two continuations per stop episode. After that it yields
with an unaccepted/manual-attention notice instead of creating an endless loop.
A new user turn resets the allowance. Missing continuation state also yields an
explicit unchecked notice. `Interrupt` and `SessionEnd` do not run the checker.
The existing `AGENT_VERIFY_TIMEOUT` bounds the owned checker process group.

`codex-completion.example.json` shows an opt-in `Stop` registration. Replace both
absolute paths and merge it alongside existing hooks rather than overwriting
them. Codex requires review and trust of non-managed definitions; see the
[official hook reference](https://learn.chatgpt.com/docs/hooks). Do not bypass
trust or install it globally to test it. First exercise a separate owned Codex
home and disposable workspace, and verify the runtime actually invokes it.

This prototype enforces only the selected acceptance contract. It does not
infer an arbitrary user's intent, prove all instructions were followed, or
establish that T3 restarts a terminated run. A passing repository test suite is
not sufficient unless it covers the requested deliverable. The existing Claude
verification/guard/format hooks are unchanged.

## CI check for application repositories

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
permissions:
  contents: read
  pull-requests: read
jobs:
  integrity:
    uses: Astatide1337/Skills/.github/workflows/test-integrity.yml@<sha>
    with:
      skills-ref: <same sha>
      approvers: your-login
```

- **Make it a required status check.** Otherwise a PR can delete the job.
- **Pin both refs to the same commit** so the checker cannot change underneath you.
- **To approve an intentional change,** apply `tests-ok:<full-head-sha>` or `gates-ok:<full-head-sha>`. Create the label with the PR's full 40-character head SHA. Only human label events from `approvers` count. New commits need new labels; unsuffixed or old-head labels never approve a change.

Run the same check locally before pushing:

```bash
python3 global-instructions/hooks/test_integrity.py --repo /path/to/app --base origin/main --head WORKTREE
```

## Limits

- **Counting is a heuristic.** It is line-based for JS/TS, Python and Go, totalled per language, so moving tests between files is not a removal. It catches deleted and skipped tests; it cannot judge whether the remaining tests are any good. A new test file that skips itself, such as integration tests gated on an environment variable, does not count as weakening.
- **Measured noise.** Replayed over the last 40 commits, it flagged 1 in `gitops` (removed experiment tests) and 2 in `Jobmark` (lint and test configuration changes). Each run took about 0.1 to 0.2 seconds per commit.
- **Not everything is watched.** It covers Makefile and justfile only through the `verify` target and its prerequisites, and `package.json` only through check scripts and the scripts they call. It does not watch every possible test-selection setting.
- **The guard matches patterns.** It catches common hook bypasses, not every way to disable a check. The CI check is the backstop.
- **The verification/guard/format registration is Claude Code only.** The opt-in
  Codex completion prototype is separate; its runtime integration must be checked.
  The CI check works for any agent or person.

## Opt-in pending-choice pre-tool prototype

`agent_gates.py choice-guard COMMAND [ARG ...]` provides a separate Claude
`PreToolUse` adapter. It sends the event JSON to the explicitly configured
checker on stdin, without a shell, in the event working directory. The checker
must exit zero and return exactly `{"status":"allow|block|unavailable",
"reason":"nonempty explanation"}` (choose one status). Only `allow` permits
the action. Blocked, unavailable, invalid, failed and timed-out checks return
exit 2 with a diagnostic on stderr; unlike the completion prototype, this
boundary never exhausts a retry allowance and then permits the action.
`AGENT_VERIFY_TIMEOUT` bounds the checker and its process group.

For an isolated Claude experiment, add a **separate** `PreToolUse` entry with
matcher `.*` and command
`python3 /trusted/Skills/global-instructions/hooks/agent_gates.py choice-guard python3 /trusted/task_choice_check.py`.
Keep the existing bypass guard. The matcher must cover shell, edit, delegation
and connector actions too; a shell command can write files and a delegate can
perform dependent work. No registration is installed by this repository.

The trusted checker must own both the explicit unresolved decision and its
actual action dependency. Register only essential user-owned choices, not every
question. Read-only actions, independent work, routine choices and choices
already settled by the request should be allowed. Record actual later user
authorization before releasing dependent actions; delivery of a question,
a recommendation, elapsed time and assistant assertions are not answers.
Unknown action semantics return `unavailable`, not an inferred permission.
Do not classify shell or nested tool actions as read-only by tool name alone.

Keep checker code and authority state outside the agent's writable workspace.
An agent-writable decision file or agent-generated oracle is not enforcement.
A real runtime adapter must bind the event to authenticated session/user events,
serialize authorization updates with dispatch, and prevent unchecked delegation
or connector calls. The subprocess tests use explicit file/action contracts and
an owned temporary authority file to exercise the interface; they do not solve
general dependency classification or constitute runtime integration evidence.

The #38 open-format sample in
`evals/results/2026-11-01-scope-recovery-batch.json` remains rejected: a question
was followed by dependent TOML edits before an answer. Both format samples'
independent-review claims remain unsupported by returned verdicts. This is
failure to apply existing authority guidance, not evidence that guidance was
absent. The separate pending-decision wording candidate remains held; no new
occurrence, wording promotion or measured behavioral improvement is claimed.

**Runtime status and next action:** the current Codex/T3 session has no
completion hook registered. A Stop hook is too late to prevent dependent edits.
This adapter implements Claude's pre-tool exit protocol only; it does not
establish a Codex pre-tool API or T3 goal enforcement. The next integration
step is an explicitly authorized disposable Claude registration with a trusted
task checker, verifying that a denied write is never dispatched and that later
authenticated authorization releases it. For Codex/T3, first establish a
supported pre-dispatch veto covering nested tools and delegates with the runtime
owner; no product edits or global installation are part of this prototype.
Leave #38 open until its literal behavioral acceptance and actual integration
are evidenced. A passing protocol test is not that evidence.
