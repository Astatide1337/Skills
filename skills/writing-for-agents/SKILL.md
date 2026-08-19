---
name: writing-for-agents
description: Write or revise instructions that another coding agent must follow reliably. Use for AGENTS.md, SKILL.md, agent prompts, runbooks, and task specifications where trigger clarity, scope, evidence, and testability matter.
---

# Writing for Agents

Write for execution, not admiration. State the outcome, triggering conditions, authority, inputs, constraints, workflow, stop conditions, and verifiable completion criteria.

## Method

1. Name the concrete behavior the document should produce.
2. Put discovery metadata in the description: what the instruction does and when it applies.
3. Separate universal rules from task-specific procedure.
4. Use imperative, observable language. Replace “be careful” with the check that demonstrates care.
5. Resolve conflicts and precedence explicitly.
6. Keep the root document lean; move detail to directly linked references.
7. Include examples only where they disambiguate a decision.
8. Test with realistic trigger, near-miss, and adversarial prompts.

Avoid personality theater, duplicated policy, unsupported metadata, hidden prerequisites, vague “best practices,” and procedures that claim success without evidence.

For skill mechanics in this repository, follow `skill-creator` and the catalog validator rather than assuming another agent harness's frontmatter fields.
