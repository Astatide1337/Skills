# Astatide Skills

A portable engineering method for AI agents: informed judgment, dependable
execution, and independently supported outcomes. One accountable engineer owns
the result. Verification challenges it. Improvement keeps only interventions
that help without narrowing valid solutions.

Use the maintained `main` branch for ordinary installation. The completed
Engineering the Engineer revision is source in this catalog; availability here
does not mean it is installed on any machine. [PREVIEW.md](PREVIEW.md) preserves
the historical comparison inputs, observed checks and disposable rollback path.
The [design record](docs/engineering-the-engineer-v2.md) is historical context,
not an always-loaded prompt. Neither instructions nor passing fixture tests
establish improved agent quality or production readiness. User-specific authority
and standing merge/deployment policies remain separate and unchanged.

The catalog is portable across compatible harnesses. Some skills reference
sibling procedures or runtime helpers; selected installation must preserve
those declared dependencies. `code-review-and-quality` needs the compatible
`verify-work` helper, which the installer includes when missing and checks
before copying. It refuses an incompatible existing helper unless that skill
was explicitly selected for replacement.

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

For a fresh checkout, select the maintained source explicitly, then list the catalog:

```bash
git clone --branch main --single-branch https://github.com/Astatide1337/Skills.git Skills
cd Skills
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
→ implement/feature; compose existing investigation/security/verification methods
  into a temporary checked sequence and report any blocked input.
```

For substantial work, inspect the owner, callers and existing automation, then
record the outcome, authority, smallest correction and acceptance. Present a
separate approval artifact only when the user or project requires it. Existing
authorization remains valid for in-scope implementation and repair. See
[plans and authority](skills/follow-instructions/references/approved-plans.md).
Read-only requests and the short path keep their own stopping conditions.

[PR/MR delivery](skills/pull-requests/SKILL.md#complete-authorized-delivery) owns
completion: affected behavior, independent review, material repairs, publication,
current-head checks and host merge eligibility. A draft is intermediate; a
review-ready flag is not merge readiness. Use native watches and runtime
continuation, retaining a compact record before interruption. Never merge or
enable auto-merge. Self-learning and automatic rule promotion remain paused.

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
  references/approved-plans.md explicit approval gates and authority
  references/principles/   detailed, selectively loaded decision rules
  references/case-studies.md selectively loaded public contrasts
  examples/                three primary-grounded instructional exercises
  playbooks/               investigate, design, implement, performance,
                           migrate-operate, review, issues, document-teach,
                           and parallel procedures
skills/<domain-skill>/SKILL.md
skills/deslop/SKILL.md          code-diff cleanup; use unslop for prose
global-instructions/AGENTS.md
evals/cases/workflows.json  optional composition and execution diagnostics
evals/workspace_evidence.py runner-owned Git baseline/evidence contract
evals/fake_tracker.py       isolated publication fixture
evals/results/               sanitized review-unit summaries
```

For worked decisions and their limits, use the
[case index](skills/follow-instructions/references/case-studies.md).
The supplied tracker fixture remains a deterministic evaluator-contract
boundary only. It is not a live tracker integration, and its results are never
product or agent verification.

## Application verification ownership

Skills owns judgment: [verify-work](skills/verify-work/SKILL.md) chooses expectations,
interprets failures and decides which evidence a change invalidates. Application
CLIs own supported deterministic operations and compatibility. Resolve a release
at an authorized setup boundary, or explicitly select a current development
revision when no release exists; retain identity throughout the task. Do not
silently upgrade active tools or copy application manifests into Skills.

[Native CLI discovery](skills/verify-work/references/agent-clis.md) covers the actual
Linktree/Shrunk package owner and Keelbox lifecycle CLI. Inspect current help;
Keelbox manages Kubernetes development resources and does not verify arbitrary
application outcomes. T3 owns collaborative browser interaction when available;
follow its current capability and ownership documentation. `internet-reach` and
its obsolete Zen bridge are retired, without a replacement browser wrapper.

Normal installation never prunes removed or unrelated skills. For an explicit
retirement in a selected destination:

```sh
./scripts/install.sh --retire internet-reach --target /path/to/disposable/skills
```

Only recognized historical package bytes are retired. Extra files, changed bytes
or links cause refusal; preserve and reconcile local customizations separately.
The obsolete `--agent-clis-source` option and pinned installer are removed; use
the CLI project's supported build/pack/install method into a task-owned prefix.
See [PREVIEW.md](PREVIEW.md) for comparison and rollback without global changes.

## Portable lint

Use the [portable lint procedure](skills/code-review-and-quality/references/portable-lint.md)
for supplemental Python/TypeScript checks without adding app configuration.
Its setup helper creates an explicitly external locked runtime; the lint runner
does not install packages or alter target source. The public entrypoints are:

```sh
python skills/code-review-and-quality/scripts/setup_portable_lint.py --runtime /path/to/fresh-external-runtime
python skills/code-review-and-quality/scripts/portable_lint.py --workspace /path/to/app --scope changed --base REF --runtime /path/to/external-runtime --receipt /path/to/new-external-receipt.json
```

Explicit files remain the default, with deliberate changed/tracked/directory
discovery available. Native checks remain independently required; portable
coverage and debt comparison have their own evidence boundaries. The owning
procedure documents exact tools, rules, suppression limits and unavailable
contexts. React Doctor is not included.

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

Complete the candidate workflow and deterministic checks before a deliberate
comparison using the currently authorized, runtime-verified model and settings. Freeze both catalogs, organic tasks, settings, tools,
budget and held-out acceptance; use the same model/settings in both arms and
retain actual failures and unavailable outcomes. Installed procedures and
passing harness tests do not establish improved model efficacy. See the
[evaluation procedure](skills/skill-creator/references/evaluation.md).

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
Execution support is gated separately: an executable fixture is not proof of a
supported native lifecycle. Historical contract-pilot results cover their
recorded cases/revisions only; they do not restrict this complete candidate or
establish its efficacy. The fixture task remains available as a deterministic
diagnostic:

```bash
uv run inspect eval evals/skills.py@workflow_fixture_pilot --max-samples 10
```

The native `workflows` task runs a pre-launch boundary gate. A case is
unscored/blocked when a required effect is outside the runner's observed
boundary; missing observations are never treated as success. The established
local native case is `workflow-native-local-repair`, which checks the actual
edited checkout and runs its supplied regression test. New approval/resume
cases require observed ordering and their own support gate; unsupported peer
review, real CI and remote effects remain unmeasured. A local workflow does not
establish live tracker, pull-request, deployment, browser or adversarial behavior.

That local workflow runs candidate supplemental checks first, then a
runner-controlled copy of the original acceptance regression against the final
workspace. The check imports the candidate's changed implementation, so
replacing `test_bug.py`, restoring the bug after a passing supplemental command,
or mentioning an exception in a source comment cannot satisfy behavioral
acceptance. The runner-owned regression is separate from the candidate's own
tests and is reported as optional local contract evidence, not live product
verification.

For a fair native comparison, select both catalog arms explicitly. The baseline
must point at an explicitly frozen accepted revision; both arms must use the same actual
user policy when comparing only Skills changes;
the no-catalog control is an optional diagnostic, not the baseline:

```bash
uv run inspect eval evals/skills.py@workflows \
  -T arm=candidate \
  -T candidate_skills_root=/path/to/candidate/skills \
  -T candidate_global_instructions=/path/to/actual-user-policy.md
uv run inspect eval evals/skills.py@workflows \
  -T arm=baseline \
  -T baseline_skills_root=/path/to/accepted/skills \
  -T baseline_global_instructions=/path/to/actual-user-policy.md
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

The historical application examples are context, not flagship quality standards.
Browser QA is a matching-surface check using the actual local server, supported
data setup and native browser tools (T3 when exposed). A screenshot or passing build
without the interaction is not a browser result. If the app's required
database or browser setup is unavailable, report that blocker instead of
fabricating a UI or using the tracker fixture as a substitute.

## Safety and provenance

- Installer work is local filesystem copying only.
- Credentials, cookies, and external service tokens do not belong in skills.
- Bundled skill scripts are preserved for an agent to use when appropriate;
  the installer and validator do not execute them.

See [`catalog.yaml`](catalog.yaml) for the catalog's source provenance.

## Local verification

Run `uv sync --frozen` and `make verify` for catalog validation and the complete
offline unittest suite (no model calls). Use Python 3.13, Node 24 and Bubblewrap
with user namespaces enabled, as in CI. Provision the locked supplemental lint
tools once outside the checkout, then export their path for the tests:

```sh
uv run --frozen python skills/code-review-and-quality/scripts/setup_portable_lint.py --runtime /path/to/skills-lint
export SKILLS_LINT_RUNTIME=/path/to/skills-lint
make verify
```
