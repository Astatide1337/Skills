# Worked exercise: resume the accepted task, then inspect live state

Use when authorized implementation will cross a real interruption. This is an
**original instructional exercise**, informed by Anthropic's
[long-running-agent account](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).
That account reports lost context, premature completion and recovery through
progress artifacts, repository inspection and actual behavior checks. The task
and observations below are hypothetical, not an industry agent transcript or a
successful local trial.

## Problem and consequential decision

A user authorized a team-settings form and its PR, with three acceptance points:
save a valid name, preserve entered text after rejected validation, and reject
writes by a read-only member. Publication is allowed; merging is not. The agent
has implemented the happy path and opened a draft when its session must stop.
Local tests passed, but browser recovery and independent review remain pending.

The tempting handoff is “form implemented; tests green.” A fresh agent can
mistake that milestone for the objective and either stop or polish unrelated UI.
An idempotency key for saving the name would address duplicate writes, but would
not retain the missing acceptance points, publication authority or review gate.

Before interruption, update the **existing task record** with the objective and
three acceptance points, authority, checkout/branch and PR identity, current
artifact, exact evidence and remaining gates. Include the failed approach when
it matters: “toast-only errors lose the entered name; inspect the submit handler
and its server response.” End with the next useful action, not a new project
ledger. See the owning [checkpoint guidance](../references/durable-checkpoints.md).

## Resume and evidence

On resumption, the agent reads that record and inspects the live checkout,
working changes, PR head/base, review and check state. Suppose the target branch
has advanced and the current server rejects empty names while the UI clears the
field. The recorded happy-path pass remains useful for its original revision;
it cannot certify this recovery behavior or the updated integration state.

The agent reproduces the rejection, fixes the form-state owner, runs valid,
rejected and denied-write paths, then continues the requested PR delivery under
[`pull-requests`](../../pull-requests/SKILL.md). A usable receipt identifies the
tested revision/instance, action and observed state for each original acceptance
point. “Checkpoint read” is not evidence that the missing work was completed.

## Valid alternative and limits

If the runtime reliably preserves the existing task record, reuse that facility
instead of creating a checkpoint file. A tiny uninterrupted edit needs neither.
If live evidence reveals a required human approval, finish independent work and
retain the exact gate and next action. Do not invent approval.

A saved record does not schedule execution. Exercise an actual resumed context
through the runtime's supported facility before claiming runtime continuation;
passing the record manually to a fresh agent proves only context recovery.
