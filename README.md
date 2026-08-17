# Astatide Skills

This repository is the source of truth for the reviewed Agent Skills catalog.
It contains plain filesystem skills, with one installable directory per skill:

```text
skill-name/
  SKILL.md
  scripts/      # optional
  references/   # optional
  assets/       # optional
```

The catalog currently contains 24 skills. `catalog.yaml` records the source
repository, exact source commit, original source path, trust classification,
profile, and installed path for every exported skill. Each `SKILL.md` carries
the runtime-facing `name` and `description` frontmatter, so Codex, Claude Code,
and other Agent Skills-compatible harnesses can discover the same metadata from
the filesystem. Bundled scripts and reference material were copied with their
skill and remain available through relative paths. Imported local archives are
identified by their SHA-256 digest instead of a Git commit.

The previous MCP Skills Gateway served these files over read-only MCP tools.
That service is retired. Skills are now installed by copying the selected
directories into the harness's local skill directory; no runtime server,
downloader, or skill-related MCP connection is required.

## Install

List available skills:

```bash
./install.sh --list
```

Install every skill into the detected Codex/Claude/project directory:

```bash
./install.sh --all
```

Install selected skills into an explicit target:

```bash
./install.sh --target ~/.codex/skills --skill systematic-debugging --skill writing-plans
```

The target is the directory that directly contains skill directories, not the
parent harness directory. When `--target` is omitted, the installer prefers
`~/.codex/skills`, then `~/.claude/skills`, then a project `.agents/skills`
directory. If more than one target is plausible, pass `--target` explicitly.
Selected skill directories are replaced verbatim on every install; no merge
logic is used.

## Validate

Run the local migration and Agent Skills checks:

```bash
./scripts/validate-skills.sh
```

The validator checks the catalog count, one-level skill layout, required
frontmatter, naming limits, description limits, and catalog-to-filesystem
coverage. It does not execute skill-bundled scripts.

## Provenance and safety

- The catalog is pinned to reviewed upstream commits; it does not fetch content
  at install or runtime.
- Installer copies are local filesystem operations only.
- Credentials, cookies, and external service tokens do not belong in skills.
- Bundled scripts are preserved for an agent to run when appropriate, but the
  repository installer and validator never execute them.

See [`catalog.yaml`](catalog.yaml) for the complete migration inventory and
source provenance.
