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
./scripts/install.sh --all --target ~/.claude/skills
```

Install selected skills instead:

```bash
./scripts/install.sh --target ~/.claude/skills \
  --skill systematic-debugging --skill web-interface
```

Without `--target`, the installer detects a Codex, OpenCode, Claude, or
project `.agents` directory. Pass an explicit target whenever more than one is
present. Each selected skill directory is replaced as a complete copy.

## Global instructions

[`global-instructions/AGENTS.md`](global-instructions/AGENTS.md) is the
portable source for cross-repository working defaults. Installing it is always
an explicit, user-controlled action and is separate from skill installation.

## Task playbooks

When a catalog skill applies, `follow-instructions` is the single entry point:
it chooses one primary task process, attaches only the domain skills that own
the decisions, records permitted effects separately, and loads supporting
procedures from `skills/follow-instructions/playbooks/`. It is not used for a
plain conceptual answer and does not grant merge or deployment authority.

Examples:

```text
Fix the broken search filter and run its regression.
→ implement/bug + systematic-debugging; workspace write; no PR requested.

Investigate the tenant lookup failure and create one issue; do not edit code.
→ investigate/read → issues/create; source inspection, one tracker write/readback,
  and no workspace, PR, merge, or deployment effect.

Design and execute a one-off offline reproduction package from these sanitized
snapshots; do not contact production or create a permanent workflow.
→ custom/compose; compose existing investigation/security/verification methods
  into a temporary checked sequence and report any blocked input.
```

The first line is the requested outcome; it is not a new command language. The
coordinator preserves literal prohibitions, uses `pull-requests` for explicit
publication, and applies `production-safety`/`security-and-hardening` when
those boundaries are in scope. Parallel work is an optional modifier and ends
with an integrated check.

The implemented package map is intentionally small:

```text
skills/follow-instructions/
  SKILL.md                 coordinator and route table
  playbooks/               investigate, design, implement, performance,
                           migrate-operate, review, issues, document-teach,
                           custom, and parallel procedures
skills/<domain-skill>/SKILL.md
global-instructions/AGENTS.md
evals/cases/workflows.json  composition and execution fixtures
evals/workspace_evidence.py runner-owned Git baseline/evidence contract
evals/fake_tracker.py       isolated publication fixture
evals/results/               sanitized review-unit summaries
```

For the second example, the agent reads `lookup.py`, records the finding in the
supplied local tracker with one `create`, fetches that issue with `get`, and
stops before editing the repository or opening a PR. The fixture is only a
deterministic evaluation boundary; it is not a live tracker integration.

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

The workflow path keeps the existing evaluator entry points. Verify discovery
and run the deterministic fixture smoke with:

```bash
uv run inspect list tasks evals/skills.py
uv run inspect eval evals/skills.py@workflow_fixture_smoke --max-samples 1
```

`workflow_fixture_smoke` uses a disposable fake tracker and is not a live
GitHub/GitLab integration. Native comparisons are separate, finite, and must
use the same model, tools, permissions, and budget for baseline and treatment.

Workspace evidence and native execution require Bubblewrap (`bwrap`) with user
and mount namespaces enabled. The preflight checks the disposable workspace
and the read-only `/usr`, `/bin`, `/lib`, `/lib64`, `/etc`, `/proc`, `/dev`, and
temporary `/tmp` mounts. There is no unsafe host fallback. The local collector
supports trusted synthetic fixtures only; remote, live, and adversarial
execution remain unsupported. Contained Git subprocesses do not contain every
Python read or native-agent operation.

The workflow dataset labels cases as `execution-ready` or `routing-only`.
Only the six supplied execution-ready cases run in `workflows` and the pilot;
the other fourteen are classification cases and are reported as behaviorally
unmeasured. Run the deterministic pilot with:

```bash
uv run inspect eval evals/skills.py@workflow_fixture_pilot --max-samples 6
```

For a fair native comparison, select both catalog arms explicitly. The baseline
must point at the last accepted checkout and its matching global instructions;
the no-catalog control is an optional diagnostic, not the baseline:

```bash
uv run inspect eval evals/skills.py@workflows \
  -T arm=candidate \
  -T candidate_skills_root=/path/to/candidate/skills \
  -T candidate_global_instructions=/path/to/candidate/global-instructions/AGENTS.md
uv run inspect eval evals/skills.py@workflows \
  -T arm=baseline \
  -T baseline_skills_root=/path/to/accepted/skills \
  -T baseline_global_instructions=/path/to/accepted/global-instructions/AGENTS.md
```

The pilot summary records exact revisions, case IDs, repetitions, and limits;
generated binary `.eval` logs are ignored and are not review evidence.

## Safety and provenance

- Installer work is local filesystem copying only.
- Credentials, cookies, and external service tokens do not belong in skills.
- Bundled skill scripts are preserved for an agent to use when appropriate;
  the installer and validator do not execute them.

See [`catalog.yaml`](catalog.yaml) for the catalog's source provenance.
