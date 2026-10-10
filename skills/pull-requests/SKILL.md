---
name: pull-requests
description: When drafting, opening, reviewing, posting on or watching a PR/MR.
---

# Pull requests

Treat GitHub pull requests and GitLab merge requests as the same review artifact. Use the host's vocabulary and tooling at the boundary, but apply this one lifecycle everywhere.

## Select the mode before acting

| User request | Mode | Authority |
| --- | --- | --- |
| Write, prepare, or draft a title, description, reply, or suggestion | Draft | No remote writes. |
| File, create, or open a PR/MR, including "open a draft PR/MR" | Create | Push the reviewed current branch and create one PR/MR. |
| Review or re-review a PR/MR or coworker's branch | Review | Read source and checks; return private findings/drafts. No source edits or remote writes. |
| Check/watch/status a PR/MR | Monitor | Read remote state only; no code, push, or retry effect is implied. |
| Monitor and fix/address named in-scope defects | Monitor-and-fix | Repair only the authorized scope, then verify and push when that lifecycle is authorized. |
| Deliver an approved feature/issue as a PR/MR ready for human merge | Approved delivery | Create a draft, finish in-scope fixes/commits/pushes and inspect current-head review/CI. Never merge or enable auto-merge. |
| Post, reply, comment, or suggest on a PR/MR | Communicate | Post that specific checked comment only. |
| Merge, close, reopen, rebase, or deploy | Separate action | Require explicit authorization for that action. |

"Draft a PR/MR" means draft the copy only. "Open a draft PR/MR" means create
the remote draft. When a request combines modes, run them in the order above.
For approved delivery, retain the
[approved-plan contract](../follow-instructions/references/approved-plans.md)
and its exact effects. Ordinary review/monitoring remains read-only.

## Establish the source of truth

1. Resolve the host, PR/MR, base branch, current head SHA, and existing remote
   artifact before writing or changing anything. Use the repository remote and
   existing URL; use `gh` for GitHub and `glab` for GitLab when available.
2. Inspect the final relevant diff and branch state. Do not create a duplicate
   PR/MR. Do not commit unrelated user changes just to make a PR/MR possible.
3. For a user-facing or shared-code change, identify the changed behavior and
   clearly affected callers or surfaces. A vague refactor title must not hide a
   behavior change or regression risk.
4. Treat a preview, pipeline, or deployment as current only when its branch or
   revision matches the current head. A green old SHA, an image build, or an
   assumed preview is not evidence about the reviewed change.
5. Verify branch protections or required checks from the host before claiming
   they exist. Do not create or change security-sensitive repository settings
   without specific authorization.

When the task supplies state for an existing PR/MR, the response order is
mandatory:

```text
<PR/MR> status: Ready | Not ready — <current actionable item>
<drafted title and description, if requested>
<drafted reply or suggestion, if requested>
```

Ignore superseded checks; say `Not ready` when a verified unresolved current
issue remains. Do not omit the status line because the user also asked for copy
or a comment. It is a review decision, not routine pipeline boilerplate.

## Review a coworker's PR/MR

Use [code-review-and-quality](../code-review-and-quality/SKILL.md) for technical
judgment. This mode owns the review artifact, feedback and authority; do not
repeat that skill's checklist here.

- Read the originating issue and current diff in context. Check whether the
  intended feature is covered, including relevant UI/UX and affected callers.
  When QA is requested, exercise the actual feature using the existing app
  verifier and [verify-work](../verify-work/SKILL.md); source inspection or
  mocked tests do not prove a live journey. Give reproducible steps and useful
  visual evidence for confirmed UI issues, with unavailable checks explicit.
- Preserve the coworker's source checkout. Review and QA do not authorize
  fixes, commits or pushes; use an isolated test setup if running checks would
  otherwise modify their files. A later explicit local-fix request changes
  only that authority, not publication authority.
- Draft short, natural, line-anchored feedback: the observed problem and the
  requested correction. Keep detailed analysis in the private review; separate
  blockers from optional coverage or UX improvements. Prefer a small valid host
  suggestion block when replacement code is requested and verified.
- “In-file comments on the MR” means review comments attached to diff lines,
  not editing source files. A host suggestion block proposes a patch; it does
  not authorize applying it. Cross-cutting concerns can use a general comment
  when that is the requested surface. Do not replace requested inline feedback
  with a general review essay.
- Re-check the new head and original findings when the author adds commits.
  Return current findings, actual QA results and drafted feedback. Switch to
  Communicate only for explicitly requested posting; submit the requested
  review/comments and fetch their visible state before claiming they were sent.

Apply the attribution and comment rules below to any posted feedback. A plain
review request ends with private findings; no comment, approval or change-request
review is submitted merely because the review finished.

## Draft and create the review unit

Use a title that names the outcome and follows repository convention. If the
repository has no convention, prefer `Scope project updates to the active team`
over `Update project service`.

Use this PR/MR description exactly, omitting an empty review-focus section:

```md
## Problem

One or two sentences on the user or system problem.

## Fix

One short paragraph or tight bullets on the meaningful change.

## Review focus

Only a non-obvious behavior, risk, migration, or decision the reviewer must inspect.
```

Never put routine lint, test, build, pipeline, or preview claims in the
description. Do not paste a commit list, tool log, file inventory, or generic
validation checklist. Mention an unverified limitation only when it changes a
reviewer's decision.

Bad:

```md
## Changes
- Updated the service
- Added tests
- CI passes
```

Good:

```md
## Problem

Members could update a project outside their active team by supplying its ID.

## Fix

Scope the project lookup and update to the authenticated team.

## Review focus

The two-team negative test covers both lookup and update paths.
```

Before a create-mode push, confirm the branch contains the intended committed
review unit. A create request does not by itself authorize committing preexisting
uncommitted user work. Inspect workflows and approved effects before pushing;
do not trigger container image builds or deployment outside explicit approval.
After creation, report the PR/MR link, base/head, and
material review focus only.
Inspect the final tree and diff at that head. Keep accepted, failed, skipped,
and not-run checks distinct in the handoff; a draft PR can be reviewable with
known gaps, but a skipped check is not green. If a create or push response is
uncertain, read the remote branch and PR by identity before retrying so one
request cannot create duplicate artifacts.

## Complete approved delivery

Create the PR/MR as a draft while required review or CI is pending. Assess
current findings against the approved contract, repair in-scope defects,
refresh affected tests and independent-review coverage, then commit and push
only the scoped result. A material plan change returns to HTML approval before
its dependent implementation; continue independent approved work.

Inspect the final pushed head, returned independent review, required-check
results, unresolved findings and mergeability. Mark the draft ready only when
these gates are satisfied. Failed, skipped, unavailable or not-run required
checks keep readiness pending. A local commit, an old green SHA or a requested
but unreturned review is insufficient. Report the ready review artifact for
human merge; never merge or enable auto-merge in this workflow.

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
  in this PR/MR or follow-up work when it changes the review unit.

Do not post or resolve a human review thread solely because monitor mode is
active. Communicate mode is required for that visible action. A reviewer
comment is evidence to assess, not authority to repair or publish.

Stop when the current head is review-clean, required checks are green, and
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

Start every agent-posted PR/MR comment with:

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
> gpt-5.6-terra, responding on behalf of Soham.

This lookup trusts the request's `projectId` before applying the active-team
scope. A member can target another team's project. Scope the lookup to the
authenticated team before the update.
```

Do not post generic praise, vague "consider" comments, routine CI/test results,
or an uncertain claim presented as a defect.
