# Astatide Skills

A lean engineering catalog for repository-native agents. Keep native search,
editing, shell, browser and project commands as the baseline. Load specialist
guidance for a decision it can improve; optional tooling must earn its setup
and maintenance cost.

## Daily workflow

Inspect the affected owner and callers, establish expected behavior, implement
a complete useful slice, exercise the real path, review correctness and
unnecessary complexity, and complete authorized delivery.

Clear corrections take the short path. Substantial features use a concise
working plan when helpful. Formal approval documents and prototypes are used
when requested or needed for a consequential user decision, not as an automatic
prerequisite for implementation. Review depth follows risk and uncertainty.

- `follow-instructions` routes repository work without becoming a second runtime.
- `architect` owns interfaces and state, including dataflow/failure-path questions.
- `code-review-and-quality` owns correctness and conditional structural review.
- `deslop` uses Ponytail-informed minimalism without always-on hooks.
- `verify-work` interprets evidence; project-local verifiers own actual app actions.
- Debugging, security, UI, performance, research and teaching retain focused owners.

The [principles](skills/follow-instructions/references/principles.md) adapt P stack.
Focused references synthesize methods from Cursor's thermonuclear review, gstack,
Trail of Bits and Impeccable. These are original local procedures, not installed
copies of whole upstream frameworks. See [catalog.yaml](catalog.yaml) for sources.

## Optional tools

[Tool selection](skills/follow-instructions/references/tool-selection.md) describes
when Context7, Serena, Knip, axe and targeted specialists can add useful evidence.
Choose one transport per capability and use project-local commands where possible.
No extra MCP fleet, broad scan, mutation suite or service runs by default.

Missing optional tooling uses a supported native fallback with a truthful gap.
Required project checks stay required. Current release metadata is not an
installation pin: check compatibility and pin the tested stable package at adoption.
Repository packaging, competing coordinators, database memory and worktree tools
remain deferred unless they fill a specific unmet job.

## Install and recover

List names without changing anything:

```bash
./scripts/install.sh --list
```

Choose the harness target explicitly:

```bash
./scripts/install.sh --all --target ~/.agents/skills
./scripts/install.sh --all --target ~/.config/opencode/skills
./scripts/install.sh --all --target ~/.claude/skills
./scripts/install.sh --target ~/.agents/skills --skill systematic-debugging
```

Selected installation includes actual runtime and essential procedural dependencies.
The coordinator's optional route links do not install every specialist. Source
packages are validated and staged before replacement. Content receipts in
`.skills-install.json` support idempotence, divergence checks and recovery.
Packages with unowned or edited contents require explicit backup replacement:

```bash
./scripts/install.sh --all --target ~/.agents/skills --preserve-existing
./scripts/install.sh --target ~/.agents/skills --rollback
./scripts/install.sh --target ~/.agents/skills --uninstall --skill systematic-debugging
```

Backups are reported outside the discovery directory. Rollback and uninstall refuse
silent loss of changed packages; `--preserve-existing` retains them in a recovery
backup. Only receipt-owned packages are eligible for uninstall. Preserve plugin
and unrelated packages. Check unique contents before consolidating legacy discovery
paths; two same-name copies should not expose different instructions.

The optional `--agent-clis-source PATH` remains a separate explicitly selected
application-CLI installation, with its own receipt and recovery. It is not part
of default skill installation or the skill transaction. [Legacy app bindings](skills/verify-work/references/agent-clis.md)
apply only to those identified projects.

## Global instructions

[global-instructions/AGENTS.md](global-instructions/AGENTS.md) remains a portable
source, separately installed at the user's direction. Skill installation never
writes it. Machine-only GUI sudo guidance belongs in the installed personal file.
Personal authority takes precedence: commit/push may be allowed while merge,
auto-merge and deployment remain prohibited.

## Verification and evaluation

Use the project’s existing tests, lint/type checks and supported browser/API/CLI
flow. Add a project-local `.agents/skills/verify-<app>/` only for reusable app
knowledge: launch, fixtures, actions, expected results, evidence and cleanup.
Do not introduce an app CLI solely to satisfy this catalog.

Run deterministic checks in the locked environment:

```bash
./scripts/validate-skills.sh
uv run python -m unittest discover -s evals/tests
uv run inspect list tasks evals/skills.py
```

Live comparisons are separate and finite: current guidance versus lean guidance,
then one marginal addition. Select model/effort explicitly from the current supported
catalog, freeze task inputs and acceptance, and preserve failed/unavailable outcomes.
Use existing Inspect tasks; no second evaluator is needed.
Read [the evaluation procedure](skills/skill-creator/references/evaluation.md)
before native runs. Task discovery and fixtures do not prove model efficacy.

The pilot starts with two to four matched pairs (4–8 total native runs). Judge
behavior, authority and truthful evidence before speed; measure interruptions,
unique useful findings, false positives and setup cost. Trial complementary pairs
and removal only when justified. Passing both arms is not a demonstrated advantage.

Historical explicit-approval fixtures test user-requested staging, not a universal
approval rule. The fake tracker remains a contract fixture under `evals/`; it is
not a live tracker integration. Runner-owned hidden checks remain outside candidate
instructions. Native execution requires the existing verified containment and a
direct trusted executable; unsupported capabilities are unavailable, not bypassed.

## Maintenance

Update existing skill owners rather than adding competing coordinators. Keep source
provenance and license review at integration. Put deterministic rules in project
checks when practical; keep skills for decisions requiring judgment. Recheck adopted
tools on compatibility changes, advisories or failures. Remove redundant additions.

Credentials, cookies and session data never belong in the catalog. Installation
copies local packages; it does not fetch upstream code or execute bundled scripts.
