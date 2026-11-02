# Agent gates

These hooks run repository checks, detect common attempts to bypass them, and
report whether verification finished. The optional completion and choice guards
call a trusted checker for a specific task. CI can enforce the test-integrity
check when the repository requires its status.

Local hooks have documented retry limits and failure modes. They do not make
all agent actions safe or prove that every requested outcome is complete.

## What runs

| Piece | When | Effect |
|---|---|---|
| `agent_gates.py session-start` | Session start | Snapshots the repository's working tree, including uncommitted and untracked files. |
| `agent_gates.py guard` | Before `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | Snapshots any other repository the tool is about to touch. Refuses `--no-verify`, `git commit -n`, `HUSKY=0`, `SKIP=…`, `core.hooksPath` changes, and edits to the gate's state or Claude Code's hook settings. |
| `agent_gates.py format` | After `Edit`, `Write`, `MultiEdit` | Formats the file with the project's own Biome, Prettier, Ruff or gofmt, when the project configures one. Never runs a binary committed to the repository. |
| `agent_gates.py stop` | Before the agent stops | For every repository that changed this session, runs the integrity check and the verify command. Blocks failed stops within the retry limit below. |
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

Requires Python 3.11+ as `python3` and `git` on `PATH`. Verification and formatting
also require the project’s own tools.

## Opt-in task completion hook (Codex prototype)

The existing `stop` check verifies changed code. It cannot detect a missing
deliverable when the agent changed nothing. The separate `completion` command
runs a task-specific acceptance check on every `Stop`, without relying on
changes or the assistant's final wording:

```sh
python3 agent_gates.py completion python3 /trusted/task_acceptance.py < hook-input.json
```

Select and review the checker for the task. Keep its code outside directories
the agent can write. Trusting a hook definition does not protect every script
it calls. A checker written by the implementing agent is not an independent
judge of that agent’s work. The hook takes its command only from configuration,
never from the event payload, final reply or transcript.

The command runs in the event's working directory, without a shell, with the
event JSON on stdin so a trusted checker can locate the actual session's evidence.
Event fields and assistant narration are not acceptance or approval; never let
them choose a command, redefine the requirement or fabricate a returned review.
If the checker command is missing, the hook requests another continuation,
subject to the limit below. The checker must exit zero and print exactly one
JSON object with `status` and a nonempty `reason`.
Do not print credentials or other diagnostics into this output.

| Checker status | Hook behavior |
| --- | --- |
| `complete` | Allows stopping. The checker is responsible for proving the actual task outcome. |
| `incomplete` | Returns `decision: block` and the reason, requesting another native continuation. |
| `blocked`, `waiting`, `cancelled` | Allows stopping with an explicit **not complete** notice. The checker must establish the missing permission or dependency, pending operation, or cancellation from actual state; an assistant assertion is insufficient. |
| Invalid output, nonzero exit, timeout | Reports an unavailable check and requests recovery; never counts as acceptance. |

It requests at most two continuations per stop episode. After that it yields
with a notice that acceptance failed and manual attention is needed.
A new user turn resets the allowance. Missing continuation state also yields an
explicit unchecked notice. `Interrupt` and `SessionEnd` do not run the checker.
`AGENT_VERIFY_TIMEOUT` limits how long the checker and its child processes can run.

`codex-completion.example.json` shows an opt-in `Stop` registration. Replace both
absolute paths and merge it alongside existing hooks rather than overwriting
them. Codex requires review and trust of non-managed definitions; see the
[official hook reference](https://learn.chatgpt.com/docs/hooks). Do not bypass
trust or install it globally to test it. First exercise a separate owned Codex
home and disposable workspace, and verify the runtime actually invokes it.

A missing or broken hook bundle can allow an action without checking it. Verify
that the complete bundle, including `test_integrity.py`, loads and is invoked
before relying on it. Test every tool path you intend to cover. Native Codex
invocation does not establish T3 integration.

The checker proves only its explicit task requirements. A passing test suite
supports completion only when it covers the requested deliverable.

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

- **Counting is a heuristic.** It is line-based for JS/TS, Python and Go, totaled per language, so moving tests between files is not a removal. It catches deleted and skipped tests; it cannot judge whether the remaining tests are any good. A new test file that skips itself, such as integration tests gated on an environment variable, does not count as weakening.
- **Measured noise.** Replayed over the last 40 commits, it flagged 1 in `gitops` (removed experiment tests) and 2 in `Jobmark` (lint and test configuration changes). Each run took about 0.1 to 0.2 seconds per commit.
- **Not everything is watched.** It covers Makefile and justfile only through the `verify` target and its prerequisites, and `package.json` only through check scripts and the scripts they call. It does not watch every possible test-selection setting.
- **The guard matches patterns.** It catches common hook bypasses, not every way to disable a check. A required CI check provides another check at PR delivery.
- **The verification/guard/format registration is Claude Code only.** The opt-in
  Codex completion prototype is separate; its runtime integration must be checked.
  The CI check works for any agent or person.

## Opt-in pending-choice pre-tool prototype

`agent_gates.py choice-guard COMMAND [ARG ...]` provides a separate exit-2
`PreToolUse` adapter. Claude and current Codex documentation support this denial
protocol; host registration, trust and actual dispatch coverage still need their
own integration checks. It sends the event JSON to the explicitly configured
checker on stdin, without a shell, in the event working directory. The checker
must exit zero and return exactly `{"status":"allow|block|unavailable",
"reason":"nonempty explanation"}` (choose one status). Only `allow` permits
the action. Blocked, unavailable, invalid, failed and timed-out checks return
exit 2 with a diagnostic on stderr; unlike the completion prototype, this
boundary never exhausts a retry allowance and then permits the action.
`AGENT_VERIFY_TIMEOUT` limits the checker and its child processes.

For an isolated Claude experiment, add a **separate** `PreToolUse` entry with
matcher `.*` and command
`python3 /trusted/Skills/global-instructions/hooks/agent_gates.py choice-guard python3 /trusted/task_choice_check.py`.
Keep the existing bypass guard. The matcher must cover shell, edit, delegation
and connector actions too; a shell command can write files and a delegate can
perform dependent work. No registration is installed by this repository.

The trusted checker must know which decision needs a user answer and which
actions depend on it. Register only those decisions, not every question. Allow
read-only actions, independent work, routine choices and choices already settled
by the request. Record actual later user
authorization before releasing dependent actions; delivery of a question,
a recommendation, elapsed time and assistant assertions are not answers.
Unknown action semantics return `unavailable`, not an inferred permission.
Do not classify shell or nested tool actions as read-only by tool name alone.

Keep checker code and authority state outside the agent's writable workspace.
An agent-editable decision file cannot enforce the agent’s authority.
The runtime must tie the tool event to authenticated session and user events.
Serialize permission updates with dispatch so an action cannot use a stale
decision. Check delegated and connector actions too. The subprocess tests use explicit file/action contracts and
a temporary authority file controlled by the test. They test the interface, not
general action classification or integration with a runtime.

**Runtime boundary:** a Stop hook is too late to prevent dependent edits. Current
[Codex hooks documentation](https://learn.chatgpt.com/docs/hooks) covers
PreToolUse denial, including nested code-mode function calls, and Stop
continuation. Installed Codex 0.165.0 discovers the two event definitions through
`hooks/list`; discovery and trust are separate from invocation. Review exact
definitions through the supported `/hooks` flow in an owned home before testing.
Do not forge trust state or use a bypass flag.

Before claiming runtime integration, observe a denied test write, a later user
authorization that allows the write, and a failed completion check that makes
the agent continue. Cover each actual tool path: persistent `write_stdin`, hosted tools and tools that opt
out may not receive a new pre-tool event. A malformed hook can fail without
denying an action, so protocol tests are necessary but not sufficient. Direct
Codex evidence does not establish T3 invocation or resumption. T3 registration
and event coverage need their own integration tests. These examples do not
authorize global installation or product changes.
