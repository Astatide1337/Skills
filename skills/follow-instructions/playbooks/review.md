# Review / audit / re-review

## When

Use for findings on a change or audit, or a review after edits. Review-only remains read-only; fixing and posting require their own authorization.

## Inputs to establish

- Request, base/head, current diff, affected callers, checks, and desired feedback surface.
- Explicit scope and relevant acceptance, not an approval dossier.

## Steps and decision points

1. Read the final artifact in context using [code review](../../code-review-and-quality/SKILL.md). A material trust boundary adds [security analysis](../../security-and-hardening/SKILL.md).
2. Try a targeted counterexample where practical. Distinguish confirmed defects, hypotheses, preferences, pre-existing issues, and scope expansion.
3. Deduplicate findings by defect. Lead with trigger, consequence, source location, evidence, and smallest useful correction.
4. On a new head, refresh findings and affected evidence. If posting is requested, use [PR work](../../pull-requests/SKILL.md) and verify the actual write.

## Failure and recovery

Do not claim execution from source inspection. An unavailable reproducer limits confidence. A reviewer proposal grants no authority to edit, resolve threads, merge, or deploy.

## Completion evidence

Report current findings and checks with useful limits. An empty findings list is valid but does not prove absence of all defects.

## Example

Re-review authentication changes against owner and non-owner cases at the final revision.

## Near-miss

Private review does not imply posting comments or changing the source.
