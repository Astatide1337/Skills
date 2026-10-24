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

## Routing result — 2026-10-24

Run with authenticated Codex CLI 0.164.0, `gpt-6.1-sol`, low effort, one epoch
and two concurrent samples. The same instruction-discovery repair from
[PR #30](https://github.com/Astatide1337/Skills/pull/30), commit `0acba59`, was
applied to main and both candidate branches; no scorer or shared case changed; learning-loop adds three cases scored separately.

On the 34 shared cases, main scored coverage 33/34 and minimality 13/34;
learning-loop scored 32/34 and 15/34. The three added cases scored coverage
3/3, minimality 0/3: the repeated-correction request selected self-reflect as
expected, and both near-misses avoided it, but all three selected unnecessary
verification/supporting workflows. The shared coverage loss was the
Shibboleth-boundary case missing security-and-hardening. One stochastic run
cannot establish causation, but it does not clear the routing acceptance bar.

### Reassessment — 2026-10-24

A per-case comparison of the same run does not support holding on routing:

- **Shared cases.** Learning-loop matched main on 31 of 34 shared cases. It was
  better on two: `css-explanation` with no skill, and `why-legacy-timeout`
  without an extra `systematic-debugging`. It was worse on one:
  `shibboleth-boundary` missed `security-and-hardening` but kept the other
  six skills. This PR changes no security wording, coordinator route table or
  security trigger. One sample per arm cannot tell that miss from noise. Every
  arm's commonest unnecessary addition was `verify-work` (main 8,
  learning-loop 11), so that pattern predates this PR.
- **The three new cases mis-specified what correct routing is.** The two
  near-misses expected no skills at all, yet the first asks to recapture from
  a live endpoint and rerun a test, and the second asks to run a script and
  rerun lint. The property under test is that `self-reflect` is not selected
  for a first or already-enforced occurrence. Both cases did avoid it.
  Corrected expectations:
  - `first-occurrence-near-miss`: requires `follow-instructions` and
    `verify-work`; allows `production-safety` (live endpoint); `self-reflect`
    is harmful.
  - `already-enforced-near-miss`: requires nothing; allows
    `follow-instructions` and `verify-work`; `self-reflect` is harmful.
  - `repeat-correction`: still requires `self-reflect`; allows `verify-work`,
    since the prompt asks for a fix.

  This is stricter on the policy's own behaviour: choosing `self-reflect` on
  either near-miss now fails minimality as harmful, where before it was only
  one of several unnecessary additions. Re-scoring the recorded selections
  gives 3/3 coverage and 3/3 minimality. That is a re-score, not a new run.

**Recommendation: merge after one targeted rerun.** Run the three new cases
and `shibboleth-boundary` for 5 epochs on main and on this branch:

```sh
uv run inspect eval evals/skills.py@routing -T native_model=gpt-6.1-sol -T native_effort=low \
  --sample-id route-follow-instructions-shibboleth-boundary,route-self-reflect-repeat-correction,route-self-reflect-first-occurrence-near-miss,route-self-reflect-already-enforced-near-miss \
  --epochs 5 --max-samples 2
```

Accept if all three of these hold:

1. `security-and-hardening` coverage on `shibboleth-boundary` is no more than
   one sample worse than main's.
2. `self-reflect` appears on at least 4 of 5 repeat-correction samples.
3. `self-reflect` appears on no more than 1 of 10 near-miss samples.

Otherwise, revise the `self-reflect` trigger wording and rerun. None of this
measures whether real proposals prevent mistakes; the revisit criteria above
cover that.

[Run identities and counts](evidence/2026-10-24-routing.json) and
[per-case selections and scores](evidence/2026-10-24-routing.jsonl) are the
readable evidence. All runs read back as `success`, without sample errors.
Reproduce after applying #30's same patch in each clean worktree:

```sh
export SKILLS_CODEX_NATIVE_BINARY=/absolute/path/to/native/codex
uv sync --frozen
uv run inspect eval evals/skills.py@routing -T native_model=gpt-6.1-sol -T native_effort=low --max-samples 2
```
