---
name: pull-requests
description: "Use when drafting, opening, reviewing, monitoring or responding to a GitHub PR or GitLab MR."
---

# Pull requests

Use this procedure for both GitHub pull requests and GitLab merge requests.
Use the host's terms and tools.

For Rutgers GitLab, apply the [operator approval rule](../production-safety/references/operator-profile.md#rutgers-gitlab)
before any remote write, including work under the delivery default below.

## Select the mode before acting

| User request | Mode | Authority |
| --- | --- | --- |
| Write, prepare, or draft a title, description, reply, or suggestion | Draft | No remote writes. |
| File, create, or open a PR/MR, including "open a draft PR/MR" | Create | Push the reviewed current branch and create one PR/MR. |
| Review or re-review a PR/MR or coworker's branch | Review | Read source and checks; return private findings/drafts. No source edits or remote writes. |
| Check/watch/status a PR/MR | Monitor | Read remote state only; does not authorize edits, pushes or retries. |
| Monitor and fix/address named in-scope defects | Monitor-and-fix | Repair only the authorized scope, then verify and push when authorized. |
| Implement a feature/issue, unless local-only work or another restriction applies | Approved delivery | Under the standing policy, commit/push the scoped change, create a draft and finish current-head checks and reviews. Never merge or enable auto-merge. |
| Post, reply, comment, or suggest on a PR/MR | Communicate | Post that specific checked comment only. |
| Merge, close, reopen, rebase, or deploy | Separate action | Require explicit authorization for that action. |

"Draft a PR/MR" means draft the copy only. "Open a draft PR/MR" means create
the remote draft. When a request combines modes, run them in the order above.
For approved delivery, retain the
[approved-plan contract](../follow-instructions/references/approved-plans.md)
and permitted actions. Ordinary review/monitoring remains read-only.

## Establish the source of truth

1. Resolve the host, PR/MR, base branch, current head SHA, and existing remote
   artifact before writing or changing anything. Use the repository remote and
   existing URL; use `gh` for GitHub and `glab` for GitLab when available.
2. Inspect the final relevant diff and branch state. Do not create a duplicate
   PR/MR. Do not commit unrelated user changes just to make a PR/MR possible.
3. For a user-facing or shared-code change, identify the changed behavior and
   clearly affected callers or surfaces. A vague refactor title must not hide a
   behavior change or regression risk.
4. Check that a preview, pipeline or deployment belongs to the current branch
   and revision before using it as evidence. An old passing run or an image
   build does not prove the reviewed behavior works.
5. Verify branch protections or required checks from the host before claiming
   they exist. Do not create or change security-sensitive repository settings
   without specific authorization.

When assessing an existing PR/MR, ignore superseded checks and account for
unresolved current issues. Explain a material readiness issue when it affects
the requested decision or copy; use the response format the task calls for.

## Review a coworker's PR/MR

Use [code-review-and-quality](../code-review-and-quality/SKILL.md) for technical
judgment. Use the rules below for the review output and permission to post it.

- Read the originating issue and current diff in context. Check whether the
  intended feature is covered, including relevant UI/UX and affected callers.
  When QA is requested, exercise the actual feature using the existing app
  verifier and [verify-work](../verify-work/SKILL.md); source inspection or
  mocked tests do not prove a live journey. Give reproduction steps and useful
  visual evidence for confirmed UI issues. State which checks could not run.
- Preserve the coworker's source checkout. Review and QA do not authorize
  fixes, commits or pushes; use an isolated test setup if running checks would
  otherwise modify their files. A later explicit local-fix request changes
  only that authority, not publication authority.
- Draft short comments tied to source lines: the observed problem and the
  requested correction. Keep detailed analysis in the private review; separate
  blockers from optional coverage or UX improvements. Prefer a small valid host
  suggestion block when replacement code is requested and verified.
- “In-file comments on the MR” means review comments attached to diff lines, not
  editing source files. A host suggestion block proposes a patch; it does not
  authorize applying it. Use a general comment for a concern spanning several
  files when the user requested that form of feedback. Do not replace requested
  inline feedback with a general review essay.
- Re-check the new head and original findings when the author adds commits.
  Return current findings, actual QA results and drafted feedback. Switch to
  Communicate only for explicitly requested posting; submit the requested
  review/comments and fetch their visible state before claiming they were sent.

Apply the attribution and comment rules below to any posted feedback. A plain
review request ends with private findings; no comment, approval or change-request
review is submitted merely because the review finished.

## Draft and create the review unit

Follow [Google's Writing good CL
descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)
for PR/MR titles and descriptions. Apply an explicit user format or required
repository template when present.
Write a short title naming the resulting change. Unless a required template
or user format says otherwise, use:

```md
## Summary
<The concrete problem and its effect on the user or system.>
<What changes and why this approach fits the existing codebase.>

## Verification
<The scenario exercised and observed result, with a useful evidence link.>
<Before/after image when the changed behavior is meaningfully visible.>
```

Replace the placeholders and omit inapplicable lines. Keep a small change to
a few sentences. Add **Decisions** only for a material tradeoff, compatibility
change or operational consequence a reviewer needs to assess. Add **Open work**
only to a draft with unresolved requirements. Describe the final change for a
maintainer who has not read the conversation; omit the work diary, file-by-file
recap, research notes and discarded approaches unless they explain a decision.

Verification should explain what now works and how it was observed. Do not
repeat routine CI status or test counts already visible on the PR/MR. Still run
the required checks and inspect their results; disclose failed, skipped or
unavailable checks that affect readiness. Link a relevant run or focused check
when it supplies evidence the reviewer needs. For visible results, follow
[visual evidence](../verify-work/SKILL.md#capture-useful-visual-evidence): attach
a real, labeled before/after comparison, not a mock or a screenshot of a test
count. For nonvisual changes, use the most direct observed output instead.
Recheck the description and attachment access against the final change before
submission.

In Create and Approved delivery modes, assign the PR/MR to Soham's verified
account on that host. Reuse a known identity or resolve it from the host; do not
substitute a bot account. Include the assignee in creation when supported,
otherwise add it immediately afterward. Preserve other assignees and fetch the
result to confirm assignment before reporting delivery.

Before publication, inspect documentation and comments in the diff as well as
code. Apply the [documentation
boundary](../follow-instructions/SKILL.md#documentation-boundary). Use the
temporary task workspace freely for review notes, research, and drafts. Include
findings that affect review in the PR/MR body, and keep project docs and source
comments focused on using or maintaining the change. Leave scratch material out
of the patch. Remove only unnecessary additions from this task; preserve
existing and independently edited material.

Before pushing in Create mode, confirm the branch contains only the intended
committed changes. A create request does not by itself authorize committing
preexisting uncommitted user work. Before pushing, inspect workflows for
deployments or other actions outside the requested delivery. After creation,
report the PR/MR link and the evidence or remaining issues needed for the user's
next decision. Inspect the final tree and diff at that head. Distinguish passed,
failed, skipped and not-run checks in the handoff; a draft PR can be reviewable
with known gaps, but a skipped check is not green. If a create or push response
is uncertain, read the remote branch and PR by identity before retrying so one
request cannot create duplicate artifacts.

## Complete authorized delivery

Use for an implementation task that includes a PR/MR intended for human merge.
Continue until the change is complete, verified and eligible for human merge.
Keep three states distinct:

- **Draft:** published work with remaining implementation, review or checks.
- **Review-ready:** coherent scope and evidence suitable for feedback; host
  approvals or integration checks may still be pending.
- **Merge-ready:** the requested behavior is verified and the host's current
  merge requirements are satisfied. This status never grants permission to merge.

1. Retain the original objective, authority and acceptance. Inspect existing
   requests, intended base, current head, host rules, required checks and approvals,
   unresolved discussions and mergeability. Discover project requirements from
   the current host/configuration; do not infer them from memory or a ready flag.
2. Complete implementation and actual affected-behavior checks. Obtain independent
   review of substantive work. Assess findings against the request; repair material
   in-scope defects and ordinary failing checks before handoff. Rerun affected
   checks and obtain review of the repairs. Keep optional
   preferences and valid alternative designs distinct from requirements.
3. Publish the scoped change, initially as draft when work remains. Inspect the
   failing output for any required check, repair its in-scope cause and push the
   correction. Reuse unaffected evidence; refresh what source or integration
   changes invalidate. Resolve conflicts within authorized scope without rewriting
   unrelated work. Inspect workflows before pushes to preserve delivery boundaries.
4. Wait through supported native mechanisms. Prefer the runtime's attached PR
   watch when available: register the request and let its notification resume this
   task. Otherwise use the host CLI's supported wait/watch. A progress update is
   not task termination; avoid tight polling, identical retries and empty pushes.
5. Before a real interruption, retain one compact continuation record using [the
   existing checkpoint
   guidance](../follow-instructions/references/durable-checkpoints.md). On
   resume, inspect the current head and base, checks, discussions and files
   before acting. Use the runtime to resume; saving notes does not schedule a
   run.
6. Fetch the final head and current target from the host. Confirm the requested
   work and behavior checks are complete, independent review has returned,
   material findings are resolved, required CI and approvals pass, the branch
   can merge, and the request is no longer a draft. Change
   the draft flag when appropriate and read it back. Host-accepted skipped/neutral
   checks are not executed tests; record what ran and ensure engineering acceptance
   independently covers the required outcome. Keep pending or unknown checks
   visible.

At substantive delivery or interruption, refresh the private
[delivery index](../follow-instructions/references/delivery-history.md) from the
actual task, acceptance and PR evidence. Keep later follow-up unknown until
observed. Record in-scope corrections and unresolved work without expanding the
PR description into a performance report. Index validity is not a readiness gate;
failed or interrupted work still belongs in the history.

Honor cancellation immediately: stop further implementation and perform only
safe owned-resource shutdown within the remaining authority. A hard runtime or
quota stop may prevent even a checkpoint; preserve one when possible. Neither
state is successful completion.

For an unavailable capability, missing permission, essential product decision or required
human-only approval, finish independent work while authority and runtime permit,
then record the missing input, remaining work and next action. Report the task
as externally blocked. A small self-imposed trial
budget is not a delivery suspension reason. Request legitimate required reviews
through the authorized host workflow; never fabricate approval or resolve a
disagreement merely to turn a status green.

Report completion only when the work is verified and the host permits a merge.
Keep permission to merge separate: never merge, enable auto-merge or deploy
under this delivery contract. [Host draft
behavior](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/changing-the-stage-of-a-pull-request)
and [branch
rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
explain why a ready flag alone is insufficient; the actual project remains
authoritative.

### Review budget

For every PR/MR delivered under this policy, obtain at least one independent
[returned round](../code-review-and-quality/SKILL.md#returned-review-rounds).
Select an available independent reviewer
through [agent selection](../follow-instructions/references/agent-selection.md).
Use the [review procedure](../code-review-and-quality/SKILL.md#returned-review-rounds)
with the selected reviewer; generic review does not require a particular model. Preserve explicit model
constraints and never count self-review as a substitute. Start with one
round covering the original outcome, scope, contracts, affected callers and
verification. Stop when the current artifact has adequate independent coverage,
material findings are resolved and the checks cover the requested outcome. A clean first round
can be enough, including for typo-only changes.

After a repair, identify which earlier conclusions it invalidates. Refresh the
affected checks and obtain independent review of those changes before claiming
readiness. This includes configuration and CI repairs. Retain unaffected evidence;
do not repeat the entire review merely because the head changed. Give each new
round a concrete coverage goal: a changed path, unresolved finding or distinct
risk. Unsupported preferences may be declined with evidence.

Continue necessary in-scope repair and review under the existing authorization.
Stop commissioning reviews when the final artifact has adequate coverage and no
material finding remains. A count of rounds is neither acceptance nor a reason
to hand unfinished work back. Honor explicit user and runtime spending limits;
if a real limit prevents required review, retain the non-ready state.

If the same approach fails twice or another round adds no useful evidence, use
[self-reflect](../self-reflect/SKILL.md) to choose a discriminating check or revise
the approach. Do not keep asking equivalent reviewers the same question, weaken
acceptance or request approval merely to continue an already authorized repair.

Verified behavior and the host's permission to merge are separate facts. If agent-owned
work is complete but a required human approval remains, report that approval
as pending. Say merge-ready only when both facts are established at the current
head. Never manufacture approval, merge, enable auto-merge or deploy.

## Monitor without scope creep

At each snapshot, record the head SHA, required-check state, mergeability, and
unresolved review items. Plain status/watch mode is read-only. On a later
snapshot:

- Ignore a failed check tied only to an older SHA, but assess unresolved review
  feedback even when it was opened earlier.
- Inspect the current source, diff, and logs before trusting a bot or reviewer
  finding. Classify it as real and in-scope, flaky/unrelated, stale, unclear,
  or scope-expanding.
- In `monitor-and-fix` mode only, fix, verify, commit, and push a real
  in-scope defect. Retry a flaky check only when the request and platform allow
  it. Never edit product code, tests, CI, dependencies, or infrastructure
  merely to silence an unrelated failure.
- Do not turn a reviewer request into quiet scope creep. Ask whether it belongs
  in this PR/MR or follow-up work when it changes the agreed scope.

Do not post or resolve a human review thread solely because monitor mode is
active. Communicate mode is required for that visible action. A reviewer
comment is evidence to assess, not authority to repair or publish.

Stop when the current head has no unresolved material findings, required checks pass, and
mergeability is known; when the PR/MR closes or is superseded; when a real
blocker needs the user; or when the user stops monitoring. "Ready to merge" is
a status, never permission to merge or deploy.

## Communicate precisely

Read the current diff and surrounding code before drafting or posting. Use a
line comment only for a stable local concern; use a PR/MR-level comment for a
cross-cutting issue. State the concrete behavior, impact, and requested change.
Offer an exact suggestion only when it is small, correct, and safe.

For an authorization finding, name the untrusted input, the trusted actor scope,
and the enforcement point. Request a lookup or update scoped to the
authenticated team/tenant rather than a generic authentication check. If the
exact field name is not supplied, name the authoritative scope without
inventing one.

Start every agent-drafted or posted PR/MR comment with:

```md
> <model slug>, responding on behalf of Soham.
```

Use the exact model slug when the runtime exposes it. Otherwise use
`> AI assistant, responding on behalf of Soham.` Never guess a model identity
or imply that a human wrote the comment.

Bad:

```md
Nice refactor! Maybe add auth here?
```

Good:

```md
> AI assistant, responding on behalf of Soham.

This lookup trusts the request's `projectId` before applying the active-team
scope. A member can target another team's project. Scope the lookup to the
authenticated team before the update.
```

Keep comments relevant to the requested review or discussion. Avoid generic
praise, vague "consider" comments, and uncertain claims presented as defects.
