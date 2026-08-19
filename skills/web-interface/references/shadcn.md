# shadcn Projects

Read this only when the user explicitly requests shadcn or the repository has
`components.json`. The local `components.json`, installed UI files, lockfile,
aliases, CSS entrypoint, selected primitive base, and package manager are the
source of truth.

1. Inspect the existing configuration and installed components before choosing
   a primitive. Reuse an installed component and its variants before writing
   custom markup or styles.
2. Respect the project's aliases, icon library, Tailwind version, semantic
   tokens, and primitive base. Do not hard-code `@/`, assume Lucide, or mix
   Radix and Base APIs.
3. Keep component composition intact: use required groups, labels, titles,
   fallbacks, and state attributes. Do not flatten a dialog, menu, field, card,
   or tabs primitive into arbitrary markup.
4. If an authorized installation or update is requested, use the project's
   pinned package runner and version. Do not use `@latest`, guess a registry,
   or fetch a package merely to discover its contents.
5. Review every generated or registry-supplied file before accepting it. Check
   imports, aliases, dependencies, accessibility, semantic tokens, and local
   modifications. Use a dry run or diff when the project authorizes it.

This catalog is offline by policy. When the necessary project configuration or
approved local registry snapshot is unavailable, state the missing evidence
instead of inventing shadcn context.
