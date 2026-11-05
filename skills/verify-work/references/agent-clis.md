# Native application tools

Before rebuilding an application operation in shell or browser code, inspect
its existing CLI, source documentation and help. Find the actual executable;
do not assume a global installation. Record its path and revision for the task.
Finding a command does not verify the requested application behavior. A
read-only review does not authorize installation or updates.

## Select once at an authorized setup boundary

Use the owning project's supported installation method. Select a compatible
release when installation or update is authorized. If a development revision is
needed, choose it explicitly. Record
the source URL, resolved commit/release, executable path, package/version
metadata and artifact or installed-file hashes in the task's existing evidence.
A checksum proves identity, not correctness. Keep that selection stable during
the task; an explicit older revision remains valid for reproduction or rollback.
Do not silently upgrade an active runtime or replace a global executable.

Skills does not own application package manifests, versions or command
semantics. Read the selected revision's prerequisites before building, and use
a task-owned prefix or disposable checkout for a trial. If you cannot establish the executable's identity or a needed capability,
report the gap and use a justified, supported alternative. Do not invent a
release channel, update command or JSON flag.

## Discover application operations

Use application-owned instructions to find its CLI and supported operations.
For recurring projects, start with [agent-clis](https://github.com/Astatide1337/agent-clis)
for Linktree/Shrunk and [Keelbox](https://github.com/Astatide1337/keelbox) for
local Kubernetes development. These are discovery pointers, not package,
command or environment contracts. Read the selected source revision and the
actual executable's help; do not infer one application's commands from another.

At an authorized setup boundary, build or install into a task-owned location
using the source owner's method. Inspect the installed metadata and hashes,
then invoke the resolved executable explicitly so `PATH` cannot select another
copy. A failed build or install is incomplete setup; diagnose that stage before
retrying. Reuse the installation while its identity remains valid.

Identify the supported operations for launch, readiness, the requested journey,
evidence and cleanup. Check their prerequisites and whether they use disposable
services, an existing application instance or shared resources. Application
operations do not widen task authority. For cluster access, verify the explicit
context and namespace; a local lifecycle tool is not a remote-cluster fallback.

Use disposable copies and owned run directories where appropriate. Select the
authentication and data environment explicitly; development login does not
prove production authentication. Do not print tokens, cookies or private data.
Choose expected behavior independently, inspect check and source/run identity,
then exercise the requested flow. Readiness does not prove that journey, and a
saved API value does not prove form recovery or persistence after reload.
Cleanup must identify and stop owned resources while retaining evidence; it
does not undo earlier application mutations or authorize deleting persistent data.

## Interpret native results

Record subprocess exits, failed and not-run checks, targets, stages, partial
effects and recovery information. Read both outer and inner results: a shell
or tool can exit successfully after capturing a failed child command. Preserve
exit statuses through pipelines. Inspect errors and supported recovery before
retrying; after an uncertain write, inspect state first.
[Verify Work](../SKILL.md) defines the evidence the task requires.
