# Engineering principles

This file is the index for the local decision principles. It is intentionally
small enough to scan. Read the linked detail only when its trigger is present;
do not load every principle for every task. The detail files are references of
the existing `follow-instructions` skill, not additional installed skills.

The structure is a local adaptation of Cursor's pstack. The upstream guide
describes 23 separate, trigger-specific principles. We read those files at
upstream commit [`889ec4b6`](https://github.com/cursor/plugins/tree/889ec4b68fa5aab0e867dad71ec3fdf386ae48f3/pstack/skills)
and retain the catalog's earlier provenance pin
[`60c641e4`](https://github.com/cursor/plugins/tree/60c641e4fad674784b30abcf9f8915dea39df38d/pstack).
This package combines overlapping ideas instead of copying pstack's text,
Cursor-only tools, model choices, or autonomy rules.

## How to apply a principle

1. Identify the trigger in the index.
2. Read the one or two linked detail files that own the decision.
3. Apply the decision rule to the actual repository, user, or system state.
4. Record the changed decision and its evidence when the work is nontrivial.

A principle name without a changed decision is not evidence of application.
Existing owner skills remain authoritative for implementation details, security,
operations, testing, and publication.

## The local set

| Local principle | Detailed reference | Pstack ideas combined | Existing owners |
| --- | --- | --- | --- |
| Solve the requested outcome | [outcome and scope](principles/outcome-and-scope.md) | Outcome-Oriented Execution, Laziness Protocol, Subtract Before You Add | `create-workflow`, `architect` |
| Establish state and ownership first | [ownership and domain](principles/ownership-and-domain.md) | Foundational Thinking, Model the Domain, Boundary Discipline, Type System Discipline | `architect`, `how`, `security-and-hardening` |
| Prefer the simplest sufficient design | [simplicity and reader load](principles/simplicity-and-reader-load.md) | Minimize Reader Load, Laziness Protocol | `create-workflow`, `code-review-and-quality` |
| Investigate causes and test behavior | [cause and behavior](principles/cause-and-behavior.md) | Fix Root Causes, Prove It Works, Test Behavior Not Implementation | `systematic-debugging`, `verify-work` |
| Scale process to consequence and uncertainty | [safe evolution](principles/safe-evolution.md) | Make Operations Idempotent, Migrate Callers Then Delete Legacy APIs, Separate Before Serializing Shared State | `production-safety`, `security-and-hardening`, `pull-requests` |
| Optimize user and maintainer experience | [experience and communication](principles/experience-and-communication.md) | Experience First | `web-interface`, `teach`, `document-teach` |
| Separate independent work before parallelizing | [leverage and verifiable units](principles/leverage-and-verifiable-units.md) | Build the Lever, Sequence Verifiable Units, Guard the Context Window, Encode Lessons in Structure | `parallel`, `create-workflow`, `teach` |
| Question a repeatedly failing approach | [challenge and adapt](principles/challenge-and-adapt.md) | Attack the Premise, Redesign From First Principles, Exhaust the Design Space | `grilling`, `architect` |
| Make claims match evidence and authority | [authority and claims](principles/authority-and-claims.md) | Prove It Works, Never Block on the Human, Encode Lessons in Structure | `verify-work`, `pull-requests`, `production-safety` |

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
