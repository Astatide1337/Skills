# 0002: Replace the self-learning pause with propose-only learning

- Status: proposed (accepted when this PR merges)
- Date: 2026-10-23
- Reverses: "Self-learning and automatic rule promotion remain paused", stated
  in the README, `follow-instructions`, `self-reflect` and `skill-creator`
- Related: 0001 (skill descriptions), proposed separately in PR #28

## Context

The pause stopped agents from rewriting their own rules: lessons drawn from
one task's context, growing rule files, and self-serving exceptions. It also
stopped repeated mistakes from ever turning into fixes. At best a lesson
became a sentence in a handoff that nobody searched later.

The owner reports these classes recurring across weeks of sessions in several
projects, each corrected by hand every time. They are listed here as
owner-reported; the session export is private:

- synthetic fixtures standing in for real API captures;
- work reported done before verification ran;
- frontend and backend request shapes drifting apart;
- internal error text reaching end users;
- work handed back to the user that the agent could have done.

## What practitioners do

Only pstack's `correct` skill has the full shape adopted here:
- a two-occurrence threshold;
- an enforcement ladder from architecture to prose;
- proof that each new check fails on the past mistake;
- a rule-to-enforcer table;
- exceptions that carry a reason, an expiry and approval.

Others contribute pieces:
- pstack `reflect`: row-by-row approval, and routing anything a check could enforce away from prose.
- Every's compound engineering: one record per solved problem, plus a refresh pass that retires stale ones.
- GitHub Copilot Memory: facts tied to code and deleted after 28 days unused.
- The Claude Code team: lessons added to a reviewed `CLAUDE.md` from pull request comments.

No one has published a controlled measurement of whether a human-approved
rule loop pays off. This decision rests on practitioner consensus and the
owner's own repeated corrections.

## Decision

- Agents record and propose; the user approves each proposal. Nothing is promoted automatically.
- **Recording:** a first occurrence becomes a Candidate row that expires after 90 days, so a second occurrence can be seen.
- **Proposing:** a proposal requires two distinct occurrences, or one that crossed a safety boundary. Breaking an existing rule means proposing a stronger enforcement level.
- **Where and how:** the fix goes to the narrowest scope (target repository by default) and the strongest enforcement that works there.
- **Proof and gate changes:** any check must be proven to fail on the past mistake. A change to a gate is marked and never ships with the code it would have failed.
- **Where rules live:** in each repository's `docs/agents/rules.md`, with a single pointer from `AGENTS.md`. Candidates expire, judgment rules carry review dates, and rows whose mistake can no longer happen are deleted.
- **Rejections:** declined proposals are recorded and not re-raised without new evidence.

Procedure: `skills/self-reflect/references/learn-from-repeats.md`.

## Revisit when

- proposals arrive faster than they can be reviewed;
- approved rules contradict each other;
- after a month, rule tables hold mostly Judgment rows with no enforcer;
- rejections outnumber approvals.

When that happens, tighten the trigger or the bar instead of returning to a
blanket pause.
