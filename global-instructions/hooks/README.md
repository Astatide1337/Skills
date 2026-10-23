# Agent gates

Hooks and a CI check that make an agent's "done" depend on checks it did not
write. Skills tell an agent what good work looks like; these make the most
common shortcuts fail loudly instead.

They exist because of failures that repeated in real sessions:

- Work was reported complete while integration tests were skipped and
  fixtures were synthetic.
- Verification happened only when the user asked for it again ("verify that
  T1 is complete", "check the git diff", "do better testing").
- A weakened test or lint rule is the easiest way for an agent to turn a red
  check green, and nothing stopped it.

## What runs

| Piece | When | Effect |
|---|---|---|
| `agent_gates.py session-start` | Claude Code session start | Records `HEAD` for the repository. |
| `agent_gates.py format` | After `Edit`, `Write`, `MultiEdit` | Formats the touched file with the project's own Biome, Prettier, Ruff or gofmt, only when the project configures it. Never installs anything. |
| `agent_gates.py stop` | When the agent tries to stop | If the repository changed this session, runs its verify command and the test-integrity check. A failure blocks the stop and shows the output. |
| `test_integrity.py` | Locally or in CI | Fails on removed tests, new skip/only/todo markers, and edits to lint, type, test-runner or verify-script configuration. Reports workflow edits for review without failing. |
| `.github/workflows/test-integrity.yml` | Pull requests in application repositories | Runs `test_integrity.py` against the base branch. A human label approves an intentional change. |

### The stop gate

- **Runs only when needed.** It runs only if the working tree is dirty or `HEAD` moved since the session started. Read-only sessions are not slowed down.
- **Verify command.** It looks for, in order: the `AGENT_VERIFY_CMD` environment variable, a `verify` script in `package.json` (run with the lockfile's package manager), or a `verify:` target in a `Makefile` or `justfile`. A repository with none of these is not verified, but still gets the integrity check.
- **Failures.** The agent sees the last 80 lines of output and is told to fix the cause, not the check. After 3 failed stops in one repository it lets the agent stop, with a notice that the work is unverified. Claude Code's own limit of 8 consecutive blocks is never reached.
- **No repeated runs.** A passing state is fingerprinted from `HEAD` and the diff, so stopping again without changes does not re-run verify.
- **Integrity check.** It compares the working tree with the session's starting `HEAD`. On a finding it blocks once and asks the agent to restore the check, or to name each weakened file in its final message if you asked for the change.

State lives in `${XDG_STATE_HOME:-~/.local/state}/agent-gates/`; override it with `AGENT_GATES_STATE`. `AGENT_VERIFY_TIMEOUT` defaults to 540 seconds.

## Install (Claude Code)

Installing is an explicit, per-machine choice, like `global-instructions/AGENTS.md`:

1. Copy the `hooks` block from `claude-settings.example.json` into `~/.claude/settings.json`, or into a project's `.claude/settings.json` to try it on one repository first.
2. Replace `$SKILLS_DIR` with the absolute path of this checkout.
3. Run `/hooks` in Claude Code to confirm all three are listed.

Requires `python3` 3.11+ and `git` on `PATH`. Nothing else.

## CI check for application repositories

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
jobs:
  integrity:
    uses: Astatide1337/Skills/.github/workflows/test-integrity.yml@main
```

To approve an intentional change, apply `tests-removed-ok` or `gates-changed-ok` to the pull request. Run the same check locally before pushing:

```bash
python3 global-instructions/hooks/test_integrity.py --repo /path/to/app --base origin/main --head WORKTREE
```

## Limits

- **Test counting is heuristic.** It is line-based for JS/TS, Python and Go. It catches deleted and skipped tests; it cannot judge whether the remaining tests are any good.
- **Measured noise.** Replayed over the last 40 commits, it flagged 1 in `gitops` and 4 in `Jobmark`. Every one was a real change to tests or check configuration: removed features, and new or tightened lint rules. Tightening is flagged too, because a new config file can also exclude things. Label it and move on.
- **Workflows are reported, not enforced.** Making them fail flagged a third of `Jobmark` commits, mostly routine pipeline upkeep.
- **Some configuration is not watched.** `Makefile` and `justfile` targets are left out because they change too often to be useful signals. Pin a `verify` script in `package.json` if that matters for a repository.
- **Claude Code only.** The hooks use Claude Code's hook format. The CI check works for any agent or person.
