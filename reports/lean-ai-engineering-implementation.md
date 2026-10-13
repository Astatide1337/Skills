# Lean framework implementation and verification

Implemented October 12, 2026, from the approved
[plan](lean-ai-engineering-plan.md). No merge, auto-merge, or deployment occurred.

## What changed

The catalog still has 23 recognizable skills. Ordinary implementation no longer
requires an HTML plan, prototype, repeated confirmation, reflection ceremony,
or blanket independent review. Review depth follows the affected boundary and
uncertainty. Existing scope, safety, negative-case, and truthful-evidence rules
remain in place.

Focused local references incorporate structural review, failure-path design,
Ponytail-informed minimalism, mechanism-based variant analysis, property/mutation
testing judgment, and targeted UX guidance. The optional tool reference keeps
native tooling first. No additional MCP server, analyzer, plugin runtime, or
always-on hook was installed. Application-specific verifiers remain project-local.

Installation now requires an explicit target, stages packages before replacement,
records content and dependency receipts, preserves divergent copies in backups,
supports rollback/uninstall, and protects dependencies of retained skills.
The README describes the actual daily path and recovery commands. Upstream method
provenance records observed revisions without claiming vendored frameworks.

Root SKILL.md content decreased from 17,730 to 15,724 words (11.3%). This is a
source-size measurement, not a claim about model token savings or effectiveness.

## Installed state and recovery

All 23 source packages match their content receipts in:

- Codex: `~/.agents/skills`.
- Claude: `~/.claude/skills`.
- OpenCode: `~/.config/opencode/skills`.

The 23 legacy Codex copies were verified identical to the previous primary copies,
then moved out of duplicate discovery. `~/.codex/skills/.system` was retained.
Both the portable and personal AGENTS.md files kept their pre-implementation hashes;
the existing user edit in the repo is not part of this implementation commit.

Installer recovery backups:

- `~/.agents/.skills-backup-13f921f4d9ae4493bb8ae5b6360109f5`.
- `~/.claude/.skills-backup-4026dfd7f9e6438fb85a2925582f33f1`.
- `~/.config/opencode/.skills-backup-240c9dbfeba647848638281ba1e7e4a0`.
- Legacy copies: `~/.codex/skills-legacy-backup-a61531e57e1f4ab5bdfbfc210348b9bc`.

Use `./scripts/install.sh --target TARGET --rollback` for the last managed
transaction. Inspect the reported backup before restoring earlier or divergent
work. The legacy backup's `migration.json` lists moved packages and their source
directory; restore only those packages if legacy discovery is deliberately needed.
Do not erase unrelated plugins or shared dependencies.

## Verification actually performed

- Catalog validation: 23 skills, 23 behavior cases, 14 routing cases, 63 workflow cases.
- Locked full suite: **247 tests run: 246 passed, one optional real app-CLI test skipped**.
- Ruff passed on the new installer and installer tests. Existing evaluator/test
  files retain their baseline lint debt; comparison found no new diagnostics.
- Diff whitespace check and static CI-boundary check passed. CI includes the new
  installer test module; no remote pipeline result is claimed.
- Idempotent reinstallation reported every Codex package unchanged.
- Independent review caught and verified the fix for uninstalling a dependency
  while leaving its caller installed. Final review inspected raw pilot logs and
  independently verified all three installed targets and global-file hashes.

## Live pilot and limits

Using Codex CLI 0.162.1, `gpt-6.1-sol`, low effort, and no paid/model behavior
grader, the existing Inspect runner executed four runs: current and lean guidance
on a tenant-filter repair and a small count-label correction. All four passed
runner-owned behavior and workspace-policy checks, including untouched cases.
Both arms passing establishes no quality advantage. Small samples and cache
variation do not support a general speed or cost claim.

The first two samples failed before model launch because legacy setup scripts
staged an absent AGENTS.md. The setups and actual Git-bootstrap tests were fixed;
personal globals were not substituted for repository instructions.

The authorized feature fixture was blocked in both arms before model launch
because the runner cannot observe absence of all its prohibited effects. Its
constraints were retained. Unit checks establish that its hidden behavioral
acceptance rejects incorrect implementations; they do not establish live feature
delivery. Final-answer scores without a constrained contract are unavailable,
not passes. Earlier failures and unavailable outcomes remain in local logs.

Optional-tool adoption, real application browser journeys, and broader organic
task comparisons remain conditional future trials, not claimed verification.
