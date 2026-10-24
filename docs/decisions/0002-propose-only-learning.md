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

## Routing evidence and limits — 2026-10-24

The original authenticated Codex CLI run used `gpt-6.1-sol`, low effort, one
epoch and two concurrent samples. The same startup repair from
[PR #30](https://github.com/Astatide1337/Skills/pull/30), commit `0acba59`, was
applied to every arm. Under the then-current expectations, main scored shared
coverage 33/34 and minimality 13/34; learning-loop scored 32/34 and 15/34.
The three added cases scored coverage 3/3 and minimality 0/3.

These scores do **not** measure the effect of this learning policy. The routing
solver reads only shipped skill names/descriptions and global instructions,
then calls the native CLI with `with_skills=False`. This PR changes skill bodies
and references, not those descriptions or global instructions. The revised
four-case comparison therefore presents identical model inputs in both arms.
The earlier Shibboleth security-skill miss cannot be attributed to this policy
from this experiment; nor can the two improved shared selections.

A model-free capture of the actual routing solver confirmed matching prompt
and schema hashes and model/effort/settings for the Shibboleth case and all
three learning cases. The baseline received the same added cases; scoring
metadata stayed outside model input. The planned five-epoch paired rerun was
not started: forty calls under the same treatment would estimate routing
variation, not the intervention. See
[input identity evidence](evidence/2026-10-24-routing-input-identity.json).
This capture checks input construction, not native execution or containment.

The added cases also needed expectation repairs:

- A repeated correction requires `follow-instructions` and `self-reflect`;
  `verify-work` is optional because the prompt asks for a fix.
- First occurrence and already-enforced near-misses require no named skill;
  `follow-instructions` and `verify-work` are valid optional companions. The
  live-endpoint case also permits `production-safety` without assuming that
  the endpoint is production. Routine focused verification does not by itself
  require the full verification workflow.
- Both near-misses explicitly classify `self-reflect` as harmful. This improves
  diagnostic labeling; it does not strengthen the existing binary minimality
  score, which already fails on either harmful or unnecessary additions.
  Allowing legitimate companions broadens the accepted outputs deliberately.

The three historical selections rescore to 3/3 coverage and 3/3 minimality
under these corrected expectations. That is a retrospective re-score, not a
new model run or independent validation of the expectations.

**Recommendation:** remove the routing-based hold and the proposed paired
routing rerun as a merge gate. Review this as a human-approved policy change;
do not claim measured prevention of recurring mistakes. If execution evidence
is wanted, expose the changed policy bodies using the existing execution task
and freeze expectations before generation: a repeated correction produces a
scoped proposal without unauthorized adoption; a first occurrence produces
only the permitted candidate behavior; existing enforcement is used rather
than replaced by another rule. Reduced recurrence needs evidence from actual
subsequent work, with the revisit criteria above retained.

[Original run identities and counts](evidence/2026-10-24-routing.json) and
[per-case selections and original scores](evidence/2026-10-24-routing.jsonl)
remain unchanged, including failed selections. All original runs read back as
`success` without sample errors; that means execution completed, not that the
learning policy was proven effective.
