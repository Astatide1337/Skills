# 0001: Skill descriptions name what, when and key terms

- Status: accepted pending routing eval
- Date: 2026-10-23
- Reverses: `498ac2e` (2026-10-05), "Keep skill descriptions compact and
  focused on activation cues", which set an 80-character budget

## Context

The 80-character budget produced descriptions like `When reviewing a diff or a
material code change.` They name a situation but not the capability or the
words a user types. A description is the only part of a skill an agent sees
before choosing it. The coordinator's own description was circular (`When
catalog skills apply`).

Evidence against the short form:

- Anthropic's skill authoring guidance says the description "should include
  both what the Skill does and when to use it", in the third person, with
  specific key terms. It sets a 1,024-character limit, and its own examples
  run about 150 to 180 characters.
  ([best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices))
- In Vercel's agent evals, a skill an agent could load on demand went unused
  in 56% of cases. Discovery, not content, was the bottleneck.
  ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals))
- Real session history showed users re-typing procedure (ticket templates,
  "verify everything", "review this branch") that existing skills cover. That
  suggests the skills were not being selected.

The reason for the original budget still holds: every description is loaded
into context for every task, so length has a cost.

## Decision

- Raise the local budget to 200 characters. 22 skills come to about 4.4k
  characters.
- Each description is one line in the third person: what the skill does, then
  `Use when` with situations and trigger words, then at most one non-trigger
  that prevents a collision with a neighbour (`deslop`/`unslop`,
  `skill-creator`/`writing-for-agents`).
- `global-instructions/AGENTS.md` points to `follow-instructions` for
  non-trivial work, so the coordinator is reachable without relying on its
  description alone.

## Verification

Before merging, run the routing eval against both revisions with the same
model and effort:

    git switch main && uv run inspect eval evals/skills.py@routing
    git switch skill-triggers && uv run inspect eval evals/skills.py@routing

Keep this change if coverage does not drop and minimality does not get worse.
If it does, record the result here and revert.
