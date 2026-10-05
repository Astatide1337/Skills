# Principle provenance and background

Optional context for attribution or a broader engineering-method discussion.
It is not task-start reading.

The structure is a local adaptation of Cursor's pstack. The upstream guide
describes 23 separate, trigger-specific principles. We read those files at
upstream commit [`889ec4b6`](https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack/skills)
and retain the catalog's earlier provenance pin
[`60c641e4`](https://github.com/cursor/plugins/tree/60c641e4fad674784b30abcf9f8915dea39df38d/pstack).
The current verification and boundary pass also read the actual
[Encode Lessons in Structure](https://github.com/cursor/plugins/blob/7022c81efb48d8b5eb15498ce6043a3bd74b694c/pstack/skills/principle-encode-lessons-in-structure/SKILL.md),
[Boundary Discipline](https://github.com/cursor/plugins/blob/7022c81efb48d8b5eb15498ce6043a3bd74b694c/pstack/skills/principle-boundary-discipline/SKILL.md),
[Make Operations Idempotent](https://github.com/cursor/plugins/blob/7022c81efb48d8b5eb15498ce6043a3bd74b694c/pstack/skills/principle-make-operations-idempotent/SKILL.md),
and [Create Verification Skill](https://github.com/cursor/plugins/blob/7022c81efb48d8b5eb15498ce6043a3bd74b694c/pstack/skills/create-verification-skill/SKILL.md)
at commit `7022c81efb48d8b5eb15498ce6043a3bd74b694c`.
This package combines overlapping ideas instead of copying pstack's text,
Cursor-only tools, model choices, or autonomy rules.

## The principal-engineer lens

This is an engineering operating method, not a career ladder. It supports
principal-level habits by making these decisions explicit:

- turn ambiguous goals into observable outcomes and small deliverables;
- understand domain ownership, interfaces, and long-term change cost;
- choose trade-offs using user impact, reliability, security, and evidence;
- create leverage through reusable checks, clear boundaries, and teaching;
- coordinate independent work without surrendering ownership;
- leave the repository easier for the next engineer to understand and change.

It cannot supply product strategy, organizational alignment, staffing choices,
or human mentorship. Those remain decisions for the responsible engineer and
stakeholders. A small repository should not inherit enterprise ceremony merely
to resemble a principal-engineer framework.

## External calibrators

These sources calibrate the local lens; they are not additional required
reading. They reinforce a few durable ideas that also appear in the detailed
references:

- [GitLab's principal-engineer framework](https://handbook.gitlab.com/handbook/engineering/careers/matrix/development/dev/principal/)
  describes organization-scale technical leadership, ambiguity reduction,
  trade-off evaluation, deep technical work, and teaching. The local limit is
  deliberate: a skill can guide engineering decisions, but it cannot create
  organizational alignment or mentorship.
- [Google's code-review standard](https://google.github.io/eng-practices/review/reviewer/standard.html)
  balances progress with code health and asks reviewers to use technical facts
  rather than preference. [Its small-change guidance](https://google.github.io/eng-practices/review/developer/small-cls.html)
  supports the local preference for reviewable, reversible units.
- [Google SRE's simplicity guidance](https://sre.google/sre-book/simplicity/)
  treats simplicity as a reliability prerequisite. The local adaptation asks
  what complexity buys the current outcome; it does not copy SRE operations
  ceremony into ordinary edits.
- [DORA's continuous-delivery guidance](https://dora.dev/capabilities/continuous-delivery/)
  measures delivery and reliability outcomes at system level. The local
  workflow uses the same caution about observable outcomes, without turning a
  small supervised task into a universal benchmark.

These are standards and observations, not proof that this package improves
agent performance. The evidence for this package remains the source-grounded
walkthroughs, actual project checks, and clearly labeled limitations.
