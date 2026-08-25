# Astatide Skills

The reviewed, installable Agent Skills catalog. Each directory in `skills/` is
self-contained and portable across compatible harnesses.

```text
skills/<skill-name>/
  SKILL.md
  scripts/      # optional
  references/   # optional
  assets/       # optional
```

`catalog.yaml` records each skill's source, pinned revision or archive digest,
trust classification, and installed path. Skills are copied locally at install
time; the catalog does not fetch or run remote content.

## Install

List the catalog:

```bash
./scripts/install.sh --list
```

Install every skill into an explicit harness directory:

```bash
./scripts/install.sh --all --target ~/.codex/skills
./scripts/install.sh --all --target ~/.config/opencode/skills
```

Install selected skills instead:

```bash
./scripts/install.sh --target ~/.claude/skills \
  --skill systematic-debugging --skill web-interface
```

Without `--target`, the installer detects a Codex, Claude, or project
`.agents` directory. Pass an explicit target whenever more than one is present.
Each selected skill directory is replaced as a complete copy.

## Global instructions

[`global-instructions/AGENTS.md`](global-instructions/AGENTS.md) is the
portable source for cross-repository working defaults. Installing it is always
an explicit, user-controlled action and is separate from skill installation.

## Validate and evaluate

Run deterministic structure and catalog checks:

```bash
./scripts/validate-skills.sh
```

The optional Inspect evaluation fixtures live in `evals/`. To verify task
discovery without making a model call:

```bash
uv sync --frozen
uv run inspect list tasks evals/skills.py
```

Run live evaluations only deliberately: they use the locally authenticated
Codex CLI and can execute model-generated code inside its workspace sandbox.

## Safety and provenance

- Installer work is local filesystem copying only.
- Credentials, cookies, and external service tokens do not belong in skills.
- Bundled skill scripts are preserved for an agent to use when appropriate;
  the installer and validator do not execute them.

See [`catalog.yaml`](catalog.yaml) for the catalog's source provenance.
