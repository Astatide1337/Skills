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

The catalog currently contains 16 skills. `catalog.yaml` records the source
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
./install.sh --target ~/.codex/skills --skill systematic-debugging --skill web-interface
```

The target is the directory that directly contains skill directories, not the
parent harness directory. When `--target` is omitted, the installer prefers
`~/.codex/skills`, then `~/.claude/skills`, then a project `.agents/skills`
directory. If more than one target is plausible, pass `--target` explicitly.
Selected skill directories are replaced verbatim on every install; no merge
logic is used.

## Validate

Run the deterministic catalog, reference, dataset, and Agent Skills checks:

```bash
./scripts/validate-skills.sh
uv run python -m unittest discover -s tests -v
```

The validator checks the catalog count, one-level skill layout, required
frontmatter, naming limits, description limits, catalog coverage, relative
Markdown links, and the Inspect dataset. The installer tests use a temporary
target and do not touch an installed harness. CI runs these deterministic checks
on pushes and pull requests; it does not make model calls.

## Evaluate

Behavior evaluation uses [Inspect AI](https://inspect.aisi.org.uk/) and
[Inspect SWE](https://meridianlabs-ai.github.io/inspect_swe/) rather than a
repository-specific runner. `evals/skills.py` exposes one representative catalog
task. It runs Codex CLI in a Docker sandbox with every catalog skill available;
the same task accepts `with_skills=false` for a no-skill baseline.

Install the pinned evaluation environment and verify task discovery without a
model call:

```bash
uv sync --frozen
uv run inspect list tasks evals/skills.py
```

Run treatment and baseline only when Docker and model credentials are available:

```bash
uv run inspect eval evals/skills.py@catalog --model <provider/model>
uv run inspect eval evals/skills.py@catalog -T with_skills=false --model <provider/model>
```

Inspect owns sandbox execution, transcripts, retries, scoring, logs, and result
viewing. Keep cases in `evals/cases/catalog.json` representative and shared;
do not create a separate harness or a mandatory suite for every skill.

## Provenance and safety

- The catalog is pinned to reviewed upstream commits; it does not fetch content
  at install or runtime.
- Installer copies are local filesystem operations only.
- Credentials, cookies, and external service tokens do not belong in skills.
- Bundled scripts are preserved for an agent to run when appropriate, but the
  repository installer and validator never execute them.
- Live Inspect evaluations can execute model-generated code only inside their
  configured Docker sandbox and are never part of automatic CI.

See [`catalog.yaml`](catalog.yaml) for the complete migration inventory and
source provenance.
