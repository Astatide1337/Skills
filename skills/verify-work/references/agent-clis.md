# Installed application CLIs

Use the Linktree CLI for Linktree verification. It requires the installed
Shrunk CLI package to start its real local Shrunk API. These tools do not drive
unrelated repositories.

From the Skills checkout, install skills and the pinned CLI together:

```sh
./scripts/install.sh --all --target "$HOME/.agents/skills" \
  --agent-clis-source /path/to/agent-clis
```

The installer builds the exact reviewed revision
`7048e748fd890340bbc03399b0dc1d619091af67`, packs all three private packages
(`@agent-clis/core`, `@agent-clis/shrunk-cli` and `@agent-clis/linktree`), and
installs them under the user's local data directory. It verifies the Linktree
package's required Shrunk dependency, then writes `linktree-agent` and
`shrunk-agent` launchers into `~/.local/bin`. Its receipt records package
versions, source revision, artifact hashes and installed-file hashes. Building
requires Node 24+, Git, Corepack with pnpm 12.8.1 and npm. The installer does
not publish packages, change shell configuration or install system packages.
For an installation conflict, the CLI helper's `--help` exposes explicit
`--prefix` and `--bin-dir` alternatives; never delete an unrelated executable.

Probe `linktree-agent commands --json` and the relevant `COMMAND --help` before
using commands. If PATH does not include the user bin directory, invoke
`~/.local/bin/linktree-agent` explicitly. The installed `shrunk-agent` is the
required service runtime used by Linktree; it does not replace the separate
Shrunk application checkout and Python environment needed to run the service.
A missing CLI is a setup gap; use the installer or report the exact prerequisite
instead of assuming another app's CLI is compatible. No install is implied by
an ordinary read-only review.

For a real run, inspect `start --help`, then use `start`, `doctor`, the requested
domain commands and `cleanup`. Node 24+, Linux, Playwright Chromium, application
dependencies and a compatible explicitly selected `mongod` remain prerequisites;
CLI installation and command discovery alone do not prove a live journey.
Use a disposable app copy/run outside the author's checkout. Select development
or real local CAS authentication explicitly; development login does not prove
CAS behavior. Named scenarios require independently selected private maps.

Inspect structured checks, source/run identity and fresh screenshots/recordings
before claiming success. A mocked Go service proves local integration only.
Cleanup stops owned resources and retains evidence; it does not undo prior
application mutations. Commands and replacement browser automation both remain
subject to the user's authority. For other apps, reuse their own existing
tooling or report a missing adapter.
