# Worked exercise: delivery continues after a red check and a real finding

Use when the user authorizes implementation and PR/MR delivery. This is an
**original instructional exercise** grounded in GitHub's
[current-commit check rules](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks),
[review semantics](https://docs.github.com/en/pull-requests/reference/pull-request-reviews)
and [`gh pr checks` interface](https://cli.github.com/manual/gh_pr_checks).
The changes and outcomes below are hypothetical, not a real PR receipt. The
authoritative completion contract is [`pull-requests`](../../pull-requests/SKILL.md).

## Problem and tempting failure

A user requests a filtered CSV export and a merge-ready PR, while forbidding
merge. The draft contains an exporter, unit tests and documentation. CI fails
on an integration assertion: the download omits the active status filter.
Meanwhile, an independent reviewer finds that the download endpoint does not
apply the existing team-access check. The list page does, so screenshots and
unit tests with an unrestricted fixture did not expose the defect.

“Draft opened; CI needs attention” hands ordinary authorized engineering back
to the user. Re-running CI without inspecting its failure changes no evidence.
Adding another export abstraction before tracing the filter and permission
owners makes the correction harder to judge.

## Better decision and evidence

Inspect the failed run at its actual head and trace the request through the
existing filter parser and authorization owner. Preserve the failing export
case. Reuse those mechanisms in the endpoint; do not infer that the page guard
protects a separate request. Add a denied-team case that attempts the download
directly, and verify a permitted filtered download against actual returned rows.

After the focused checks pass, have independent review examine the substantive
correction and remaining findings. Push the correction and inspect the new head,
target and actual host rules. Wait through the runtime's supported host watcher;
in a terminal-only session whose installed help supports it,
`gh pr checks <url> --required --watch` is a native option. Its pending exit code
is not a test pass. Inspect failing output and repair an in-scope cause before
checking the corrected head again.

Old-head success cannot establish new-head readiness. GitHub may evaluate the
test merge commit, and a skipped job can satisfy host status rules without
testing the export. Retain the direct behavior evidence as well as the required
host results. Before handoff, read back draft state, material review resolution,
required approvals and mergeability against the current target. A ready flag
alone proves none of those. Do not merge.

## Valid alternative and limits

A reviewer may prefer moving authorization into a shared download handler. If
the existing endpoint boundary already enforces it correctly and negative tests
prove that boundary, explain the evidence and resolve the disagreement on its
merits; a new abstraction is not required to satisfy review.

If required approval is human-only and unavailable, complete every independent
correction and check, request review through the authorized workflow, then
report the exact approval gate as pending. External approval is not permission
to fabricate a green state or bypass protection. Conversely, a normal failed
check is a next action, not an external gate.
