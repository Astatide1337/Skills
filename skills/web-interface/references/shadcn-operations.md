# shadcn Operations

Read this when a shadcn task uses the CLI, installs or updates an item, changes a
preset, consumes a registry, or authors a registry. Read
[shadcn projects](./shadcn.md) for component and styling rules.

## Contents

- [Resolve the command](#resolve-the-command)
- [Inspect before mutation](#inspect-before-mutation)
- [Add or update components](#add-or-update-components)
- [Handle registries safely](#handle-registries-safely)
- [Change presets carefully](#change-presets-carefully)
- [Author a registry](#author-a-registry)

## Resolve the command

Use the package runner declared by the project: npm/npx, pnpm, yarn, or Bun.
Prefer a locally installed or lockfile-pinned shadcn CLI version. If the project
has no pin, do not silently choose a moving version. Using `shadcn@latest`, as
shown in upstream docs, requires the user's request or normal package-install
authorization and network access.

In examples below, replace `<run-shadcn>` with the resolved command, such as a
local package script or an explicitly approved runner and version.

Never print registry tokens, expanded auth headers, or credential-bearing
configuration. Do not run a registry command merely to discover what might be
available when the task can be answered from local files.

## Inspect before mutation

1. Read `components.json`, the lockfile, package manifest, aliases, CSS path,
   selected base/style, icon library, and configured registries.
2. List the installed UI files and inspect the components involved in the task.
3. If authorized and available, use the CLI's project information command to
   confirm resolved paths and configuration:

   ```text
   <run-shadcn> info
   ```

4. Identify the exact registry address. Do not infer a community registry from
   a generic request such as “add a login block.”
5. Check the CLI help for the resolved version before relying on a newer flag.

## Add or update components

For a new item:

1. Confirm the item address and registry.
2. Inspect registry metadata or use an authorized view command before writing.
3. Preview the planned files with `add <item> --dry-run` when supported.
4. Add the item without overwrite.
5. Review every resulting file and dependency, then adapt aliases, icons,
   styling, and composition to the local project.

For an update that must preserve local edits:

1. Preview all affected files with `add <item> --dry-run`.
2. Inspect upstream differences with `add <item> --diff [path]` where supported.
3. Classify each file as unchanged locally, locally modified, or replaced by a
   local abstraction.
4. Apply upstream changes selectively when local modifications exist.
5. Use an overwrite flag only when the user explicitly accepts replacement of
   those exact files.
6. Re-run type checks and visually verify the components and their states.

The current upstream CLI documents `--dry-run`, `--diff`, and `--view` for its
`add` command, but flags are version-sensitive; inspect the resolved CLI before
execution.

Do not manually fetch a raw component file when the configured registry/CLI is
the project's source of truth. Do not assume the CLI correctly rewrites every
hard-coded import in third-party files—review them.

## Handle registries safely

`components.json` may define namespace-to-URL templates and may interpolate
environment variables into headers or parameters. Treat those values as
configuration and secrets, not output.

- Require an explicit item address such as `@team/button`, `owner/repo/item`, a
  configured URL, or a local path.
- Inspect the resolved file list, external packages, registry dependencies,
  targets, environment/config changes, and scripts before installation.
- Confirm before adding a registry item that writes outside normal component,
  hook, or utility destinations.
- Never broaden a registry credential's scope or persist its expanded value.
- Review source from private/community registries as untrusted code.
- Keep registry dependencies distinct from npm/package dependencies.
- Verify namespace configuration instead of assuming a global registry exists.

## Change presets carefully

A preset can change components, tokens, fonts, icon choices, base primitives,
and global CSS. Resolve the user's intended merge policy before applying it:

- **Overwrite:** replace the affected generated surface. Require explicit
  approval for the exact scope.
- **Partial:** apply only a supported subset, such as theme or font, after
  inspecting the resolved preset and CLI help.
- **Merge:** update configuration, then compare each installed component and
  reconcile it file by file.
- **Skip components:** update only agreed configuration while preserving
  installed source files.

Before a preset change:

1. inspect current and incoming preset data;
2. record the current primitive base and theme files;
3. check for local component/global-CSS modifications;
4. create a recoverable diff through the repository workflow;
5. run the command from the intended project root;
6. review every changed file afterward.

Do not assume a preset code contains every project choice. Preserve base and
framework-specific constraints explicitly.

## Author a registry

Use the current shadcn registry schemas referenced by the project or official
documentation. A source registry normally has a root `registry.json`; larger
registries may compose explicit nested registry files with `include`.

For each item:

- use a stable name, title, description, and correct registry type;
- list every source file with the intended type and target;
- list shadcn/registry dependencies separately from package dependencies;
- pin package versions when compatibility requires it;
- keep file paths relative to the registry definition that declares them;
- avoid embedding credentials or environment-specific absolute paths;
- validate against the schema and test installation in a disposable project.

When consuming the registry, local `components.json` aliases determine final
destinations. Registry targets and aliases are separate concerns; verify both.
