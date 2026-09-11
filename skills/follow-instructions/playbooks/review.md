# Review / audit / re-review

## When

Use for findings on a revision, a security/quality audit, or a re-review after
the head changed. Review-only is read-only; fixes and posting are separate
requested follow-ons. Use [`code-review-and-quality`](../../code-review-and-quality/SKILL.md)
for the five-axis review and [`security-and-hardening`](../../security-and-hardening/SKILL.md)
for a material trust boundary.

## Inputs to establish

- exact repository, base/head revision, requested scope and current threads;
- whether the result is private findings, suggested patch, posted review, or
  authorized fixes;
- requirements, affected callers/tests/interfaces, security/operational scope,
  and current checks that actually match the head.

## Steps and decision points

1. Pin the current head and read the diff in context. Inspect ownership,
   callers, state transitions, UX and relevant security/performance effects.
2. Run a targeted counterexample or reproducer when it can distinguish a real
   defect. Classify each item as confirmed defect, hypothesis, preference,
   pre-existing, stale, or scope-expanding; do not invent a comment quota.
3. For each material finding record severity/confidence, location, trigger,
   impact, evidence, smallest correction, and regression expected. In a
   re-review, re-run or re-inspect the original case on the new head.
4. Decide readiness only from current findings and checks. If publication is
   requested, use [`pull-requests`](../../pull-requests/SKILL.md), submit rather
   than leave pending, and fetch the visible review/threads afterward.

## Failure and recovery

If the head changes, discard conclusions tied only to the old revision. If a
reproducer or source is unavailable, label the finding unverified. A reviewer
comment is not authority to edit, resolve, merge, or deploy; fixes invoke the
implementation route and their own verification.

## Completion evidence

Return current-head findings, checks and scope, with posted-review URL/state
only when fetched back. Say whether conclusions are executed, source-derived,
or unverified. “No findings” is not proof that all bugs are absent.

## Example

Re-review a changed authentication patch by pinning the new SHA, rerunning the
two-identity negative case, and posting one submitted finding if the bypass
remains.

## Near-miss

“Review this diff here; do not change or post anything” inspects and reports
findings but does not quietly fix code or call a review API.
