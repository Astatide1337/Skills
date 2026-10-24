# Learn from repeated mistakes

Turn a mistake that keeps happening into a proposal that makes it hard to
repeat. Agents record and propose; the user approves. Nothing here grants
permission to edit a repository, the Skills catalog or global instructions
without that approval.

Adapted from pstack's `correct` skill (`cursor/plugins`, commit
[`8b3326d9`](https://github.com/cursor/plugins/tree/8b3326d99fd4b993cb33a24dad8af03175c642c5/pstack/skills/correct)),
with candidate tracking and expiry from GitHub Copilot Memory and Every's
compound engineering.

## 1. Notice a mistake

Start when the user, a reviewer, a revert or a failed acceptance check shows
a mistake the agent made. Name the class, not the instance: "hand-written
fixtures instead of captured API responses", not "the T12 sketch fixture".

## 2. Look for earlier occurrences

Read the target repository's `docs/agents/rules.md` if it exists: Enforced,
Judgment, Candidates and Rejected. Then run a targeted search for this one
class: `git log --grep`, reverts, review comments, and session history if the
harness exposes it. Search for the class you have; do not sweep history for
new lessons.

## 3. Decide what to do

| What you found | Action |
| --- | --- |
| First occurrence | Fix it. Add a Candidate row in the same commit when the task already authorizes writes; otherwise mention it in the handoff. No proposal. |
| A second distinct occurrence, or a matching Candidate row | Propose a fix (section 4). |
| A rule that already exists was broken | That rule is too weak. Propose moving it up one enforcement level. |
| One occurrence that crossed a safety boundary (data loss, secrets, production, auth) | Propose a fix now. |
| A matching Rejected row | Do not re-propose unless this occurrence is new evidence; link the rejection. |

Two distinct occurrences means two separate instances of the same class. One
failure retried twice is one occurrence.

## 4. Propose

Choose along two axes and say why. **Scope:** the narrowest place that fixes
it (see `skill-creator`'s layers): the current task, the target repository,
global instructions, or the Skills catalog. Default to the target repository;
a lesson moves into the catalog only when it recurs across repositories or is
about how agents work. **Enforcement:** the strongest form that works there.

| Target repository | Skills catalog |
| --- | --- |
| 1. Architecture: one owner per state, one supported path, unimportable internals, delete code an agent would copy | 1. A hook or permission in `global-instructions/hooks/agent_gates.py` |
| 2. Types or schema that make the bad state unrepresentable | 2. A tested helper script (for example `verify-work/scripts/boundary_checks.py`) |
| 3. A lint rule or CI check whose error names the fix; fail only new violations if the pattern is widespread | 3. An eval case the no-guidance baseline fails |
| 4. A test that fails on the past mistake | 4. Skill text |
| 5. Rule text, for judgment calls only | |

Assume the next agent sees only the files it opens, copies the nearest
example, and takes the shortest path that compiles.

Present one block per class, then stop:

- **Class:** one line.
- **Evidence:** each occurrence, linked or quoted.
- **Fix:** scope and level, why each stronger level does not work, and the
  exact diff.
- **Proof:** the command that fails on the past-mistake revision (or a
  minimal reproduction) and passes after the fix. A check that has never
  failed is a draft. A check must run the same way locally and in CI.
- **Gate-touch:** yes or no. Does this change any test, check, threshold,
  permission or verifier? If yes, it is reviewed on its own merits and never
  ships in the same commit as code it would have failed. Per
  `measured-improvement`, an aggregate score cannot justify it.
- **Cost:** runtime, context and friction it adds to future tasks.
- **Review by:** a date, for rule-text rows and exceptions only.

## 5. Apply only what the user approves

- Approved: land it as its own commit. Add or update the row in
  `docs/agents/rules.md`. A Skills or global-instructions change follows
  `skill-creator` and `measured-improvement`.
- Rejected: add a Rejected row with the reason.
- Exceptions to an enforced rule go on the offending line, with a reason, an
  expiry date and the user's approval. Never add a blanket ignore.

## 6. Keep the table honest

Whenever you touch `docs/agents/rules.md`:

- delete expired Candidates;
- for Judgment rows past their review date, propose keep, strengthen or
  delete, with evidence of whether the mistake recurred;
- for Enforced rows whose enforcer no longer exists, propose repair or
  deletion;
- delete any row whose mistake can no longer happen.

## Where rules live

In each target repository, created on the first approved rule, never in
advance:

```text
AGENTS.md              one line: "Before proposing a rule or after a correction,
                       read docs/agents/rules.md." Plus only judgment rules that
                       must shape every task.
docs/agents/rules.md   ## Enforced   | Rule | Enforced by | Evidence | Added |
                       ## Judgment   | Rule | Trigger | Evidence | Added | Review by |
                       ## Candidates | Class | Evidence | Seen | Expires (seen + 90 days) |
                       ## Rejected   | Class | Proposed fix | Reason | Date |
```

The table stays out of `AGENTS.md`. An enforced row tells the implementing
agent nothing the check's error does not, and candidates and rejections are
noise in context loaded on every task. For the Skills catalog, the equivalent
table is `skills/follow-instructions/references/failure-to-checks.md`. Record
catalog rejections with their reason in the existing proposal PR or issue,
and search those records before proposing the same change again.

## Do not

- Generalize one task's context into a rule.
- Write a rule that eases the agent's own work at the check's expense:
  lowered thresholds, broader exceptions, skipped tests.
- Apply a proposal because it looks obviously right. Approval is required.
