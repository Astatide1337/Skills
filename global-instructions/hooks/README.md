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
- **Hooks are Claude Code only.** The CI check works for any agent or person.
