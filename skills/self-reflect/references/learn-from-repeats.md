# Learn from repeated mistakes

Turn a mistake that has happened twice into a proposal that makes it hard to
happen a third time. Agents propose; the user approves. Nothing here grants
permission to edit a repository, the Skills catalog or global instructions
without that approval.

## When this applies

- The user corrects something that has gone wrong before: in this task, in
  the repository's rule table, in commit or revert history, or in review
  comments.
- A `Close` reflection finds a lesson backed by two or more real occurrences.

A mistake class counts once it has two occurrences with evidence. Two
occurrences means two distinct instances of the same class, not one failure
retried twice. A single occurrence goes in the handoff as an observation,
nowhere else. Do not mine unrelated history looking for lessons.

## Choose the strongest fix

Assume the next agent sees only the files it opens, copies the nearest
example and takes the shortest path that compiles. Fix the class at the
highest level that works, and say why each higher level does not:

1. **Architecture.** Remove the wrong way: one owner per piece of state, one
   supported path per task, internals that cannot be imported, deleted dead
   code an agent would copy.
2. **Types or schema.** Make the bad state unrepresentable, for example shared
   types generated from the API schema instead of hand-copied payloads.
3. **Check.** A lint rule, CI step or script whose error names the file,
   type or function to use instead. If the pattern already exists widely,
   fail only on new occurrences.
4. **Test.** A test that fails on the real past mistake.
5. **Rule text.** Only for judgment calls nothing can check. Rule text is the
   weakest form: nothing fails when an agent skips it.

Prove any check or test fails on the real past mistake: run it against the
revision or a minimal reproduction of the original error. A check that has
never failed is a draft.

## Choose where it lives

| The mistake is about | Put the fix in | Record it in |
| --- | --- | --- |
| This codebase | The target repository (code, config, CI) | The repository's `AGENTS.md` rule table |
| How agents work, seen in two or more repositories | The Skills catalog, via `skill-creator` | `SCOPE.md` evidence and an eval case |
| A standing personal preference | `global-instructions/AGENTS.md` | The commit message |

Default to the target repository. A lesson moves into the Skills catalog only
when the same class shows up in more than one repository or concerns the
agent's method rather than one codebase.

## Propose

Present one block per class and stop for a decision:

- **Class:** one line naming the mistake, not the instance.
- **Evidence:** each occurrence with a link, commit, file or quoted correction.
- **Fix:** the level chosen, why higher levels do not work, and the exact
  change (files and diff, or the rule text).
- **Proof:** the command that shows the check failing on the past mistake.
- **Cost:** what it adds to every future task (runtime, context, friction).

Apply only after the user approves that specific proposal. Within an
already-authorized task, an approved repository fix lands as its own commit.
A Skills or global-instructions change follows `skill-creator` and its
measured-improvement rules.

## Rule table

Each repository that adopts a rule keeps one table in its `AGENTS.md`:

```markdown
## Rules and enforcers

| Rule | Enforced by | Evidence | Added |
| --- | --- | --- | --- |
| Fixtures come from real API captures, never hand-written | `scripts/check-fixtures` (fails without capture metadata) | PR #12, PR #15 | 2026-10-23 |
| Error text shown to users comes only from `errors.ts` | test `user-errors.test.ts` | review on #31, #34 | 2026-10-23 |
```

- When the user corrects a mistake that already has a row, it is a repeat.
  Fix it at a higher level in the same change.
- When a check enforces a rule, keep the row but delete any duplicate prose
  rule elsewhere. When a mistake can no longer happen, delete the row.
- At a `Checkpoint` or `Close`, flag rows whose enforcer no longer exists or
  that contradict current code. Propose their removal; do not keep stale rules.

## Rejected proposals

When the user declines a proposal, record the class and the reason in the
same place the rule would have lived: a `Rejected` list under the repository's
rule table, or `docs/learning/rejected.md` for the Skills catalog. Check that
list before proposing, and do not re-propose a rejected class without new
evidence.

## Do not

- Encode one task's context as a general rule.
- Write a rule that makes the agent's own work easier at the expense of the
  check: no lowered thresholds, broader exceptions or skipped tests.
- Add a persona, slogan or general best practice the model already follows.
- Apply a proposal because it seems obviously right. Approval is required.
