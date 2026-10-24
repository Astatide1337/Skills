# 0002: Replace the self-learning pause with propose-only learning

- Status: accepted
- Date: 2026-10-23
- Reverses: "Self-learning and automatic rule promotion remain paused", stated
  in the README, `follow-instructions`, `self-reflect` and `skill-creator`

## Context

The pause existed to stop agents from rewriting their own rules: lessons from
one task's context, rule bloat and self-serving exceptions. It also stopped
the loop that makes a harness improve. A recurring mistake produced, at best,
a sentence in a handoff that nobody acted on.

Session history showed the cost. The same mistake classes recurred across
weeks and were corrected by hand each time:

- synthetic fixtures standing in for real API captures;
- work reported done before verification;
- frontend and backend payloads drifting apart;
- internal errors reaching users;
- work handed back that the agent could do itself.

Practitioners who ship reliably with agents do not freeze learning. They gate
it. A mistake class must occur twice. The fix goes to the strongest
enforcement level: architecture, then types, then a check, then a test, then
text. The check is proven to fail on the past mistake, a human approves it,
and stale rules are pruned. pstack's `/correct` and `/reflect`, Every's
compound step and the Claude Code team's shared `CLAUDE.md` all follow this
shape.

## Decision

- Agents propose; the user approves. Nothing is promoted automatically.
- The trigger is a mistake class with two occurrences with evidence, or a
  user correcting a repeat.
- The fix level is chosen highest-first. Any check is proven to fail on the
  real past mistake.
- Placement defaults to the target repository: code, config and CI, plus a
  rule→enforcer row in its `AGENTS.md`. A fix goes into the Skills catalog only
  when the mistake recurs across repositories or concerns agent method, and
  then it must meet `SCOPE.md`.
- Declined proposals are recorded and not re-proposed without new evidence.
- Rules whose mistake can no longer happen are deleted.

Procedure: `skills/self-reflect/references/learn-from-repeats.md`.

## What would make us revisit this

- Proposals arrive faster than they can be reviewed.
- Approved rules start contradicting each other.
- A month of rule tables shows mostly prose rows with no enforcer.

If any of these happens, tighten the trigger or the bar instead of returning
to a blanket pause.
