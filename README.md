# Astatide Skills

The personal engineering workflow. Start with one entry skill, select a
proportionate playbook, use the existing domain skills, and verify the actual
result. The catalog is daily-use documentation first; its optional evaluator
is evidence about contracts, not a product judge.

Each directory in `skills/` is self-contained and portable across compatible
harnesses.

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

Codex's current user discovery location is `~/.agents/skills`. Install every
skill into an explicit destination:

```bash
./scripts/install.sh --all --target ~/.agents/skills
./scripts/install.sh --all --target ~/.config/opencode/skills
./scripts/install.sh --all --target ~/.claude/skills
```

The older `~/.codex/skills` path is supported both as an explicit target and as
an automatic fallback described below. Installation replaces each selected
same-name package, including local customizations; use `--target` to choose the
destination explicitly.

Install selected skills instead:

```bash
./scripts/install.sh --target ~/.claude/skills \
  --skill systematic-debugging --skill web-interface
```

Without `--target`, the installer prefers the current project's `.agents`, then
Codex's `~/.agents`, the legacy `~/.codex`, OpenCode, and Claude. Pass an
explicit target whenever more than one is present. Each selected skill
directory is replaced as a complete copy.

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
  SKILL.md                 entry point, route table, and evidence gates
  references/principles.md principle index and pstack mapping
  references/principles/   detailed, selectively loaded decision rules
  references/case-studies.md selectively loaded public contrasts
  examples/jobmark-pagination.md source-grounded worked example
  playbooks/               investigate, design, implement, performance,
                           migrate-operate, review, issues, document-teach,
                           custom, and parallel procedures
skills/<domain-skill>/SKILL.md
skills/deslop/SKILL.md          code-diff cleanup; use unslop for prose
global-instructions/AGENTS.md
evals/cases/workflows.json  optional composition and execution diagnostics
evals/workspace_evidence.py runner-owned Git baseline/evidence contract
evals/fake_tracker.py       isolated publication fixture
evals/results/               sanitized review-unit summaries
```

For the worked application example, read
[`examples/jobmark-pagination.md`](skills/follow-instructions/examples/jobmark-pagination.md).
The supplied tracker fixture remains a deterministic evaluator-contract
boundary only. It is not a live tracker integration, and its results are never
product or agent verification.

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

`workflow_fixture_smoke` and `workflow_fixture_pilot` exercise the evaluator's
runner-owned contract with a disposable fixture. They are contract diagnostics,
not live GitHub/GitLab integration, and must not be reported as product, agent,
or publication verification. Native comparisons are separate, finite, and must
use the same model, tools, permissions, and budget for baseline and treatment.

The fake tracker is intentionally limited to those optional publication-contract
diagnostics. It stays under `evals/`, is not installed with the skills, and is
not needed for ordinary diagnosis, implementation, review, or issue drafting.
Its runner-owned receipts test ordering, identity, source-read observation, and
idempotent recovery; they are fixture evidence, not proof of a live tracker or
agent behavior. Removing it would remove that contract's negative controls rather
than simplify the daily package.

Workspace evidence and native execution require Bubblewrap (`bwrap`) with user
and mount namespaces enabled. The preflight checks the disposable workspace
and the read-only `/usr`, `/bin`, `/lib`, `/lib64`, `/etc`, `/proc`, `/dev`, and
temporary `/tmp` mounts. There is no unsafe host fallback. The local collector
supports trusted synthetic fixtures only; remote, live, and adversarial
execution remain unsupported. Contained Git subprocesses do not contain every
Python read or native-agent operation.

The workflow dataset labels cases as `execution-ready` or `routing-only`.
Seven supplied execution-ready cases are available: six contract diagnostics
whose native external effects are intentionally blocked, plus one local-only
repair with a real workspace/test outcome. The other fourteen are
classification cases and are reported as behaviorally unmeasured. Run the
deterministic contract pilot with:

```bash
uv run inspect eval evals/skills.py@workflow_fixture_pilot --max-samples 7
```

The native `workflows` task runs a pre-launch boundary gate. A case is
unscored/blocked when a required effect is outside the runner's observed
boundary; missing observations are never treated as success. The supported
native pilot case is `workflow-native-local-repair`, which checks the actual
edited checkout and runs its supplied regression test. It does not establish
live tracker, pull-request, deployment, browser, or adversarial behavior.

That local workflow runs candidate supplemental checks first, then a
runner-controlled copy of the original acceptance regression against the final
workspace. The check imports the candidate's changed implementation, so
replacing `test_bug.py`, restoring the bug after a passing supplemental command,
or mentioning an exception in a source comment cannot satisfy behavioral
acceptance. The runner-owned regression is separate from the candidate's own
tests and is reported as optional local contract evidence, not live product
verification.

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

### Real repository demonstration

For a non-fixture demonstration, use an explicitly authorized public checkout
and its own native commands. In the Issue #17 review unit, the real
`pallets/markupsafe` checkout was pinned to `b2e4d9c7687be25695fffbe93a37622302b24fb1`:

```bash
git clone --depth 1 https://github.com/pallets/markupsafe.git /tmp/markupsafe-demo
uv run --project /tmp/markupsafe-demo pytest -q
uv run --project /tmp/markupsafe-demo ruff check
uv run --project /tmp/markupsafe-demo mypy
git -C /tmp/markupsafe-demo diff --exit-code
```

Those commands exercise the repository's actual source and tests. A real
checkout/test result establishes only that repository behavior; it does not
establish live GitHub publication, deployment, browser behavior, or a better
agent workflow. Do not substitute the disposable fixture or a no-model run for
that evidence.

The Jobmark example is the directly executed application path. Browser QA is a
separate matching-surface check and must use the app's local server, real local
database, and native Playwright/browser tools. A screenshot or passing build
without the interaction is not a browser result. If the app's required
database or browser setup is unavailable, report that blocker instead of
fabricating a UI or using the tracker fixture as a substitute.

## Safety and provenance

- Installer work is local filesystem copying only.
- Credentials, cookies, and external service tokens do not belong in skills.
- Bundled skill scripts are preserved for an agent to use when appropriate;
  the installer and validator do not execute them.

See [`catalog.yaml`](catalog.yaml) for the catalog's source provenance.
