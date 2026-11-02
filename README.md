# Astatide Skills

Skills for agents that develop, review and maintain software. The catalog covers
planning, implementation, debugging, verification and delivery. One agent owns
the result and resolves findings from independent review.

Install from `main`. Files in this repository are not automatically installed
on your machine. [PREVIEW.md](PREVIEW.md) records earlier experiments and how to
reproduce their disposable installations; it is not an installation channel.

Some skills depend on sibling skills or helpers. For example,
`code-review-and-quality` needs a compatible `verify-work` helper. The installer
includes that helper if it is missing and refuses to replace an incompatible
existing version unless you also select `verify-work`.

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

## Resync existing installs

Use Python 3.12+ and Git to preview a resync from a committed revision:

```bash
python3 scripts/sync.py --ref HEAD \
  --target ~/.agents/skills --target ~/.claude/skills \
  --claude-settings ~/.claude/settings.json
```

Add `--apply` to execute the plan. Repeat `--target` for any existing skill root,
including OpenCode or a project directory. Only catalog packages already present
are replaced; unrelated skills stay intact. Local package customizations are
backed up before replacement. Use `install.sh` for first-time skill installation.
The command runs on the current machine and requires no account, SSH access, or
machine inventory. It does not fetch: fetch/review the desired revision first.

`--claude-settings` is optional. It installs a versioned hook snapshot, sets
`SKILLS_DIR`, and adds the example hooks without replacing other settings or
hooks. Existing modified hook entries are preserved; review those separately to
avoid running a custom variant alongside a catalog hook.

For instruction text you explicitly want to share, add
`--instructions /path/to/your-rules.md ~/.codex/AGENTS.md` (repeatable). It creates
or updates a `skills-sync` block and preserves text outside it. The source is the
file you name, including local edits; skills and hooks come only from `--ref`.
This repository's global instructions contain personal environment rules, so
other users should provide their own source text.

Preview performs no target writes. Apply saves changed targets under
`~/.local/state/skills-sync/backups/`, verifies copied bytes and file modes, and
restores originals if a write fails. The backup receipt maps each target to its
saved original. A second identical apply makes no changes. Restart agent sessions
to load updated instructions and hooks.

## Delivery and review defaults

Under the [global instructions](global-instructions/AGENTS.md), implementation
requests normally include a scoped PR. A local-only request or another explicit
restriction overrides that default. For planning, explanation and review,
perform only the requested actions.

Every delivered PR needs independent review. The
[pull-requests skill](skills/pull-requests/SKILL.md#review-budget) sets the review
budget: usually one to three rounds, never more than five. An exhausted budget
leaves review pending; it does not waive findings or checks. Use
[Better Call Sol](skills/better-call-sol/SKILL.md) when Sol is requested or chosen.
Merging requires explicit approval. Auto-merge and deployment are prohibited.

Keep ordinary plans in the task record. Create a separate plan when the user
requests a format, a project requires approval, or a visual explanation helps
resolve a decision. Reuse approval for in-scope implementation and repairs. See
[plans and authority](skills/follow-instructions/references/approved-plans.md).

## Global instructions

[`global-instructions/AGENTS.md`](global-instructions/AGENTS.md) contains personal
working defaults and environment rules. Installing it is a separate, explicit
action; installing skills does not install these instructions.

## Task playbooks

For substantial engineering work, start with
[`follow-instructions`](skills/follow-instructions/SKILL.md). It chooses the task
procedure and loads domain guidance as needed. Clear local corrections can use
its short path. A plain conceptual answer needs no workflow setup.

Examples:

```text
Fix the broken search filter and run its regression. Keep this local.
→ implement/bug; investigate the cause if unclear; edit and test, without a PR.

Investigate the tenant lookup failure and create one issue; do not edit code.
→ investigate/read, then issues/create; inspect source, create the issue,
  and verify the posted result. Do not change source or open a PR.

Build a one-off offline reproduction from these sanitized snapshots.
Do not contact production or create a permanent workflow.
→ implement/feature; combine the relevant investigation, security and
  verification steps in a temporary workspace.
```

These are examples of task selection, not a command syntax. Preserve the user's
objective, restrictions and required output throughout the work. For each
substantial change, inspect the implementation and callers, choose the smallest
complete change, and decide how to check it. Simplify changed code before final
verification and review. Edit substantial prose for clarity, then check that its
claims match the evidence.

[PR delivery](skills/pull-requests/SKILL.md#complete-authorized-delivery) covers
publication, review findings, repairs and checks on the current head. Creating a
draft or marking a PR ready does not complete those steps. Use the runtime's
continuation and PR-watch tools when waiting; retain unfinished work before an
interruption.

For delegation, use the shared
[agent-selection policy](skills/follow-instructions/references/agent-selection.md).
Choose a model and reasoning level from the runtime's actual capabilities, based
on the task and explicit user constraints. Record the returned settings. Generic
review can use an available reviewer; a request for Sol remains a request for Sol.
The [parallel procedure](skills/follow-instructions/playbooks/parallel.md) covers
worker ownership and integration. Larger programs can use a standing coordinator
with one owner per PR. Skills do not replace the runtime's scheduler.

Useful entry points:

| Need | File |
| --- | --- |
| Select a procedure | [follow-instructions](skills/follow-instructions/SKILL.md) |
| Resolve an engineering decision | [principle index](skills/follow-instructions/references/principles.md) |
| Compare worked decisions | [case studies](skills/follow-instructions/references/case-studies.md) |
| Propose a fix for a repeated mistake | [learn from repeats](skills/self-reflect/references/learn-from-repeats.md) |
| Clean changed code | [deslop](skills/deslop/SKILL.md) |
| Revise prose | [unslop](skills/unslop/SKILL.md) |

These instructions define how agents should work. Runtime enforcement and
measured effects on agent behavior need separate evidence.

## Application verification ownership

Use [verify-work](skills/verify-work/SKILL.md) to choose checks, interpret failures
and decide which results must be refreshed after a change. Use application
CLIs for their documented operations. During authorized setup, choose a release
or, if none exists, a specific development revision. Keep that version fixed
throughout the task. Do not
silently upgrade active tools or copy application manifests into Skills.

[Native CLI discovery](skills/verify-work/references/agent-clis.md) explains where
to find Linktree, Shrunk and Keelbox and how to check their supported commands. Inspect current help;
Keelbox manages Kubernetes development resources and does not verify arbitrary
application outcomes. T3 owns collaborative browser interaction when available;
follow the runtime’s current tool instructions. `internet-reach` and
its obsolete Zen bridge are retired, without a replacement browser wrapper.

Normal installation never prunes removed or unrelated skills. For an explicit
retirement in a selected destination:

```sh
./scripts/install.sh --retire internet-reach --target /path/to/disposable/skills
```

Retirement removes only recognized historical versions. It refuses packages with
extra files, modified contents or links. Preserve and review those local changes
separately.
The obsolete `--agent-clis-source` option and pinned installer are removed; use
the CLI project’s documented build, pack and install commands in a directory
created for the task.
See [PREVIEW.md](PREVIEW.md) for comparison and rollback without global changes.

## Portable lint

Use the [portable lint procedure](skills/code-review-and-quality/references/portable-lint.md)
for supplemental Python/TypeScript checks without adding app configuration.
Its setup helper installs pinned tools outside the application checkout. The
lint runner does not install packages or edit source. Use:

```sh
python skills/code-review-and-quality/scripts/setup_portable_lint.py --runtime /path/to/fresh-external-runtime
python skills/code-review-and-quality/scripts/portable_lint.py --workspace /path/to/app --scope changed --base REF --runtime /path/to/external-runtime --receipt /path/to/new-external-receipt.json
```

The runner checks explicitly named files by default. You can also select changed
files, tracked files or a directory. Run the project’s own checks too, and report
new findings separately from existing debt. The linked procedure lists the
tools, rules, suppression limits and unsupported contexts. React Doctor is not
included.

## Validate and evaluate

Run the structural checks without model calls:

```bash
./scripts/validate-skills.sh
```

The optional evaluations live in `evals/` and use Inspect. List the available
tasks and run a deterministic fixture check with:

```bash
uv sync --frozen
uv run --frozen inspect list tasks evals/skills.py
uv run --frozen inspect eval evals/skills.py@workflow_fixture_smoke --max-samples 1
```

`workflow_fixture_smoke` and `workflow_fixture_pilot` test the evaluator with
supplied local fixtures. Their fake tracker checks ordering, source identity,
readback and recovery from duplicate requests. It is not installed with the
skills. Passing these tests does not verify a real product, tracker or PR.

Live evaluations use the locally authenticated Codex CLI and execute generated
code. Run them only within an authorized, bounded experiment. Follow the
[evaluation procedure](skills/skill-creator/references/evaluation.md) to freeze
tasks, catalogs, settings, tools, permissions, budget and independent acceptance
checks. Keep every failed or unavailable attempt. When comparing catalog changes,
use the same actual user policy in both versions:

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

The baseline must be a frozen accepted version. A run without any catalog is an
optional diagnostic, not a substitute for that comparison. Explicitly set the
model, reasoning, cases and limits using the evaluation procedure before running
these commands. Inspect's token limits do not cap the nested CLI's usage.

The local evaluator requires Bubblewrap (`bwrap`) with user and mount namespaces.
Its preflight checks the disposable workspace and read-only system mounts; there
is no fallback that runs outside the sandbox. It supports trusted synthetic
fixtures. Containing Git subprocesses alone does not contain every Python read
or native-agent operation.

A dataset's `execution-ready` label means it supplies an executable fixture. A
separate check decides whether the runner can observe the required behavior and
prohibited effects. Unsupported cases are blocked and unscored before model
launch. Local results do not prove remote publication, real peer review, CI,
browser behavior or safety against hostile inputs.

For example, `workflow-native-local-repair` checks the edited source with a
runner-controlled copy of the original regression. Replacing the visible test,
restoring the bug after a passing command, or adding an exception name in a
comment cannot satisfy that check. The candidate's own tests remain separate.
[Issue 17's report](evals/results/issue-17-pilot.md) records this comparison and
checks on a pinned real MarkupSafe checkout. Those historical results apply only
to the recorded versions and tasks.

### Issue regressions and continuation

Select opt-in issue cases from `evals/cases/skills-comparison.json` through
`workflows(case_ids=...)`. Run their valid alternatives and defect controls
without model calls:

```bash
uv run --frozen python -m unittest evals.tests.test_issue_resolution_cases evals.tests.test_issue_scope evals.tests.test_issue_completion -v
uv run --frozen python -m unittest evals.tests.test_issue_branch_scope evals.tests.test_skills_lifecycle.UserTurnLifecycleTests -v
```

The [October 31 record](evals/results/2026-10-31-issue-regressions.json) preserves
native attempts, a fixture correction and remaining acceptance for twelve
issues. These synthetic tests do not close the issues or show that one catalog
performs better. Full transcript replay, actual runtime reproduction, repeated
corrections over time and reader assessment require separate observations.

Opt-in `user_turns` metadata supplies up to eight scripted messages through
`codex exec resume` in one session. Each entry has `text` and
`allowed_paths_before`, which limits cumulative persisted edits before the next
message. The model, effort, guidance, workspace and permissions stay fixed. The
runner records responses, usage and workspace snapshots. It stops continuation
if the session ID or edit observations are missing or invalid. Ordinary runs
remain ephemeral; `approval_turn` and interruption cases use fresh sessions.

This tests scripted corrections in one session, not adaptive conversation,
children, compaction or edits restored between snapshots. Pre-turn checks forbid
Git metadata and index changes. Separate branch-ancestry cases require local
commits and runner-owned acceptance; they remain blocked because the native
profile protects `.git`. Missing, truncated or cancelled observations are
unscored; an observed scope violation fails.

Effects scores do not judge whether a question was appropriate. The scope case
has a separate response review for bounded work and accurate reporting of an
unrelated open decision. It does not measure whether the agent waited for an
answer before dependent work: that case's schema does not depend on the desktop
integration choice.

Keep raw `.eval` logs for inspection; Git ignores them. Published summaries must
identify the revisions, cases, repetitions, failures and limits. Structural
checks, grading scores and successful installation alone do not establish better
agent behavior. If the evaluator needs repair, preserve independent acceptance
and report the changed measurement separately; see
[verifier validity](skills/verify-work/SKILL.md#validate-the-measuring-instrument).

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

## Review

Review guidelines live in root `AGENTS.md`. `CLAUDE.md` imports them for local
Claude Code; `REVIEW.md` shares them with the optional hosted review service.

In a feature checkout, run `/code-review main...HEAD` in Claude Code. For a
stacked PR, use its actual base branch instead of `main`. Omit `--fix` and
`--comment` for a local report. An explicit range includes already-pushed commits.
Local review uses the existing session allowance; no hosted-review plan is
required. See [local review](https://code.claude.com/docs/en/code-review-local).

For optional Codex GitHub review, connect the repository in
[Code review settings](https://chatgpt.com/codex/settings/code-review), turn on
**Automatic review → All PRs**, and select creation/new-push events under
**Review trigger**. Alternatively enable **Follow personal preferences** with
**Personal preferences → Automatic review** on. A manual request is
`@codex review`. See [setup](https://learn.chatgpt.com/docs/third-party/github).

For GitLab, `codex exec` or local `/code-review` can inspect an MR diff without
posting. Rutgers writes, including `--comment` or `glab`, require explicit approval.
