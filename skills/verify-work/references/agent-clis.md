# Native application tools

Before reconstructing an operation in shell or browser code, inspect the
application's existing CLI, its current source documentation and actual help.
Discover executable paths rather than assuming a global installation. Record
which executable/revision the task uses; command discovery proves capability,
not the requested application outcome. No install or update is implied by a
read-only review.

## Select once at an authorized setup boundary

Use the owning project's supported installation method. Resolve the latest
available stable release from its authoritative repository when installation or
update is authorized, subject to the application's compatibility requirements.
If no release exists, explicitly select a current development revision. Record
the source URL, resolved commit/release, executable path, package/version
metadata and artifact or installed-file hashes in the task's existing evidence.
A checksum proves identity, not correctness. Keep that selection stable during
the task; an explicit older revision remains valid for reproduction or rollback.
Do not silently upgrade an active runtime or replace a global executable.

Skills does not own application package manifests, versions or command
semantics. Read the selected revision's prerequisites before building, and use
a task-owned prefix or disposable checkout for a trial. If identity or a needed
capability is unavailable, report the exact gap and use a justified supported
alternative; do not invent a release channel, update command or JSON flag.

## Linktree and Shrunk: agent-clis

The authoritative source is [Astatide1337/agent-clis](https://github.com/Astatide1337/agent-clis).
Its README describes local private packages, not a registry release. At an
explicitly selected revision, follow that README: Corepack uses the project's
`packageManager`; `pnpm install --frozen-lockfile` installs its dependencies,
`pnpm build` builds the workspace, and `pnpm --filter PACKAGE pack
--pack-destination DIR` produces the matching artifacts. Inspect the current
package manifests for package names, executable mappings and dependencies;
install all matching required artifacts together using the documented `npm
install --prefix TASK_PREFIX ...TARBALLS`. This is the package owner's method;
Skills has no second installer or permanent source pin.

For a disposable trial, archive the selected commit to a private task directory
(or use a disposable worktree), build/pack there, hash the resulting artifacts,
and install to a fresh task prefix. Inspect installed metadata against those
artifacts and record the resolved source commit. Invoke executables from that
prefix's `node_modules/.bin` so global PATH cannot silently select another copy.
Reuse this installation while its identity remains valid. A failed build or
install leaves an incomplete task prefix, not an accepted runtime; inspect the
failed stage before retrying or choosing a fresh prefix.

For Linktree, run `linktree-agent commands --json`, then the relevant
`COMMAND --help`. Prefer its registered `start`, `doctor`, domain operations and
`cleanup` for Linktree work. They own the disposable services, real browser
operations, state/readback and evidence. T3 owns general collaborative browser
interaction; an application CLI's bounded browser operation remains useful for
its supported domain. Inspect a rendered implementation with T3 when the task
requires visual/interactive assessment beyond that operation.

Shrunk has a constrained `shrunk-agent start` entrypoint, not Linktree's command
registry. Read the selected `packages/shrunk-cli/src/cli.mjs` and its usage for
accepted inputs; it does not support `commands --json` or a general `doctor`.
Prefer Linktree `start --shrunk-app PATH` when verifying Linktree with Shrunk:
the owning runtime supplies the required service arguments and owns cleanup.
The separate compatible Shrunk application checkout, Python environment,
MongoDB binary, Node runtime and browser prerequisites still matter. Inspect
current requirements rather than copying package versions from Skills.

Use disposable app copies and owned run directories. Select development versus
real local CAS explicitly; development login does not prove CAS. Do not print
private tokens, cookies or application data. Independently select the expected
behavior, inspect structured checks and source/run identity, then prove the
actual requested flow. A saved API setting does not prove an unsaved form,
Cancel, navigation recovery, authorization rejection or persistence after reload.
Cleanup stops owned resources and retains evidence; it does not undo earlier
application mutations.

## Keelbox: Kubernetes development lifecycle

The authoritative source is [Astatide1337/keelbox](https://github.com/Astatide1337/keelbox).
Read its README and `tools/release/INSTALL.md` at the chosen revision. Use a
published compatible release when one exists; otherwise select a development
revision and use the documented build/package target in a disposable copy.
Install the resulting binary only to the task prefix. Verify its checksum,
`keelbox version` (or the version option documented by that binary) and
`keelbox --help`. An installed `dev`/`commit unknown` label does not establish
source provenance; record that limitation or build the selected revision.

Keelbox owns local Kubernetes development lifecycle commands such as `doctor`,
`config`, `build`, `up`, `ps`, `logs`, `exec`, `down` and explicit volume removal.
Read current help/configuration before using them. `doctor` checks prerequisites;
it does not prove the application journey. Before cluster access, verify the
intended context and namespace explicitly under the user's policy. Keelbox is
not a universal application verifier, a remote-cluster fallback or permission
to delete volumes. Use its native lifecycle where it fits, then verify the
application's actual behavior with its own supported surfaces.

## Interpret native results

Preserve the subprocess exit and the tool's failed/not-run checks, target, stage,
partial effects and recovery information in verification evidence. Read both
outer and inner results: an outer shell or tool envelope reporting success
cannot turn a failed child operation into a passing check. Avoid piping away
an exit status. When a command fails, inspect its usable error and supported
recovery before repeating it; after uncertain writes inspect state first.
The [verification owner](../SKILL.md) defines what evidence the task requires.
