---
name: better-call-sol
description: "Runs bounded independent Sol review rounds and repairs. Use when Better Call Sol is requested or Sol is selected for review. Uses the existing review standard; never merges or deploys."
---

# Better Call Sol

Run Sol reviews using the [review standard](../code-review-and-quality/SKILL.md)
and [PR delivery budget](../pull-requests/SKILL.md#review-budget). The agent
implementing the change fixes defects and verifies the final result. Reviewers
may inspect the work; they may not edit, publish or delegate it.

## Establish the candidate

Inspect git status, the intended base and the full scoped change, including
untracked files. Preserve unrelated work. Identify the candidate by its head SHA
and uncommitted changes. Give the reviewer the requested outcome and format,
permitted actions, acceptance criteria and raw check results. Give the reviewer
access to affected callers without substituting the author's summary for the
artifact. Use the current host's documented delegation tools; do not invent tool
names or a CLI wrapper.

## Select and call Sol

Use [agent selection](../follow-instructions/references/agent-selection.md) for
capability discovery, reasoning and supported dispatch. Use a user-named Sol
version when supplied; otherwise the latest available Sol. Record the provider,
model and settings actually used. If the requested model or capability is
unavailable, finish safe independent work and report the review pending; do not
substitute. Each round is a new task in fresh context. Reviewers do not start
nested reviewers.

## Resolve and continue

Use the delivery policy's risk-based round count and hard maximum of five. Each
brief states the original requirements, reviewed revision and uncommitted changes,
permitted actions, paths to review and raw evidence. Later rounds include changed code and
open finding IDs while retaining the original outcome and access to relevant
context. Stop after a clean round when the current artifact has adequate coverage
and no unresolved material findings; another round needs a concrete reason.

For each returned finding, verify the premise. Repair a real in-scope defect and
rerun affected checks, or decline an unsupported finding with evidence. Do not
add compatibility requirements, expand scope or rewrite code solely to satisfy a
preference. Have a fresh reviewer check repairs that invalidate the earlier
review, within the same round budget. If the review is pending, the cap is
exhausted or a material disagreement remains, retain that state rather than
asserting approval. Report the reviewed revision, returned verdicts, findings
fixed or declined, and any unresolved findings or required checks.

Publishing and current-head CI belong to [pull-requests](../pull-requests/SKILL.md).
This loop does not merge, deploy or independently grant an external write.
