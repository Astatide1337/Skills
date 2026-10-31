---
name: better-call-sol
description: "Runs bounded independent Sol review rounds and repairs. Use when asked for Better Call Sol or during PR delivery. Uses the existing review standard; never merges or deploys."
---

# Better Call Sol

Orchestrate the [review standard](../code-review-and-quality/SKILL.md) and
[PR delivery budget](../pull-requests/SKILL.md#review-budget). The integrating
agent owns repairs and final evidence. A reviewer inspects; it does not gain
implementation, publication or delegation authority.

## Establish the candidate

Inspect git status, the intended base and the full scoped change, including
untracked files. Preserve unrelated work. Identify the candidate by head SHA
and its working delta; record the original outcome, required format, authority,
acceptance and raw check results. Give the reviewer access to affected callers
without substituting the author's summary for the artifact. Use the current
host's documented delegation tools; do not invent tool names or a CLI wrapper.

## Select and call Sol

Discover the available Sol model through runtime capabilities. Use a user-named
version when supplied; otherwise use the latest available Sol. Retain observed
provider/model/settings, without guessing usage or changing user effort settings.
If the requested model or delegation capability is unavailable, finish safe
independent work and report the review pending; do not silently substitute.

In T3, use `orchestrator_capabilities` for discovery and a new `delegate_task`
for every round, with role review and a fresh brief. Honor the returned next
instruction; do not poll a running delegate. Do not reuse its thread for the
next review, create top-level threads, or let reviewers start nested reviewers.
On another host, use its supported fresh-context reviewer with the same limits.

## Resolve and continue

Use the delivery policy's risk-based round count and hard maximum of five. Each
brief includes the original contract, current candidate identity, permitted
effects, coverage focus and raw evidence. Later rounds include changed code and
open finding IDs while retaining the original outcome and access to relevant
context. Stop after a clean round when the current artifact has adequate coverage
and no unresolved material findings; another round needs a concrete reason.

For each returned finding, verify the premise. Repair a real in-scope defect
and rerun affected checks, or decline an unsupported finding with evidence.
Reject invented compatibility, scope expansion and preference-only churn.
Refresh invalidated reviewer coverage under the same round budget. If the
review is pending, the cap is exhausted or a material disagreement remains,
retain that state rather than asserting approval. End with candidate identity,
returned verdicts, fixed/declined/open findings and remaining gates.

Publishing and current-head CI belong to [pull-requests](../pull-requests/SKILL.md).
This loop does not merge, deploy or independently grant an external write.
