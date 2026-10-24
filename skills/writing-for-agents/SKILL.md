---
name: writing-for-agents
description: "Writes or revises instructions for agents: AGENTS.md, CLAUDE.md, prompts, runbooks, specs, with triggers and checkable completion. Use when authoring agent-facing guidance. Not SKILL.md files."
---

# Writing for Agents

Write for execution, not admiration. State the outcome, triggering conditions, authority, inputs, constraints, workflow, stop conditions, and verifiable completion criteria.

## Method

1. Name the concrete behavior the document should produce.
2. State both the trigger and objective in the produced instructions. A reader
   must be able to answer “when do I invoke this?” and “what observable state
   should result?” without inferring either from the filename. For an Agent
   Skill, put the trigger in frontmatter; for a runbook or task specification,
   use a short applicability or trigger statement in the document itself.
3. Separate requirements, defaults and examples. Requirements bind outcomes,
   authority and evidence. Defaults allow a justified alternative; examples
   demonstrate a decision under stated conditions.
4. Name the actor, action and observation that informs the next decision. For a
   consequential sequence, state what the agent does when an observation fails
   or a required capability is unavailable. Replace “be careful” with the check
   that demonstrates care.
5. Resolve conflicts and precedence explicitly.
6. Keep the root document lean; move detail to directly linked references.
7. Include examples only where they disambiguate a decision.
8. Test the changed behavior with a realistic trigger, a near-miss and a valid
   alternative. Add a failure or interruption case when the instructions govern
   recovery or continuation. Check the outcome, not recitation of the wording.
9. Hand the instructions to a cold reader with only the declared context. Run
   the actual command or user path it prescribes, inspect the result, correct
   missing prerequisites or ambiguous steps, and rerun the corrected text.

When a rule describes a deterministic boundary, name the approved pattern,
forbidden alternative, enforcement point, and one violating fixture that is
rejected. Put the rule in the owning type, schema, lint rule, script, or CI
check when possible. Keep prose for decisions that still require judgment.

Avoid personality theater, duplicated policy, unsupported metadata, hidden prerequisites, vague “best practices,” and procedures that claim success without evidence.

Before removing a personalized rule, check current instructions and relevant
user-authored history when available. Keep task-specific exceptions scoped;
missing history is not evidence that a preference was invented.

Give agents room to choose their working method. Distinguish temporary working
material from delivered project changes, and constrain the effect that matters.
For example, “Use a temporary task workspace for research and drafts; include
only useful project documentation in the final patch” preserves exploration
while keeping scratch material out of the codebase. Apply the
[documentation boundary](../follow-instructions/SKILL.md#documentation-boundary)
to this instruction-writing task too.

Read `references/instruction-design.md` when deciding what context to include,
where it should live, how to prevent premature completion, or how to prune an
existing instruction set. Apply its no-op test before adding another rule.

For skill mechanics in this repository, follow `skill-creator` and the catalog validator rather than assuming another agent harness's frontmatter fields.
