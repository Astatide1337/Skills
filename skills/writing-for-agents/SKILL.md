---
name: writing-for-agents
description: "Writes or revises instructions for agents: AGENTS.md, CLAUDE.md, prompts, runbooks, specs, with triggers and checkable completion. Use when authoring agent-facing guidance. Not SKILL.md files."
---

# Writing for Agents

Write instructions that an agent can act on without guessing. State when to
use them, the required result, permitted actions, necessary inputs, steps,
checks and stopping conditions.

## Method

1. Identify the behavior the instructions need to change.
2. State when the instructions apply and what result the agent must produce.
   Put a skill's trigger in its frontmatter. Give a runbook or task
   specification a short applicability statement.
3. Distinguish requirements, defaults and examples. Requirements constrain
   results, permissions and evidence. Defaults allow a justified alternative.
   Examples illustrate a decision under stated conditions.
4. Name who acts, what they do and what they check before continuing. For
   consequential steps, explain what to do if the check fails or a required
   tool is unavailable. Replace “be careful” with the relevant check.
5. Resolve conflicting instructions and state which source takes precedence.
6. Keep essential steps together. Link directly to details needed only in
   particular cases. Add an example only if it resolves an ambiguity.
7. Test a realistic request, a nearby request where the instructions should
   not apply, and a different valid solution. Test failure or interruption
   when the instructions govern recovery. Judge actions and results, not
   whether the agent repeats the wording.
8. Give a fresh reader only the declared context. Have them run the prescribed
   command or user path. Fix missing prerequisites and ambiguous steps, then
   rerun the corrected procedure.

For a rule that code can enforce, name the allowed behavior, the forbidden
behavior, the enforcing type, schema, script or CI check, and a test that
rejects a violation. Put enforcement there. Keep prose for decisions that
still need judgment.

Remove repeated policy, role-playing, unsupported metadata, hidden
prerequisites and vague “best practices.” A procedure must say what evidence
supports completion.

Before removing a personalized rule, check current instructions and available
user-authored history. Missing history does not make a preference disposable.
Keep exceptions tied to the task that needs them.

Let agents choose how to explore and draft. Restrict the effects that matter:
use temporary working files for research, but include only useful project
documentation in the final patch. Apply the
[documentation boundary](../follow-instructions/SKILL.md#documentation-boundary)
to this task too.

Read [instruction design](references/instruction-design.md) when choosing
context, arranging references, preventing premature completion or pruning an
instruction set. Before adding a rule, ask what action would change without it.

Use `skill-creator` and this repository's catalog validator for skill files.
Do not copy frontmatter fields from another agent runtime without checking
that this one supports them.
