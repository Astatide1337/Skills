---
name: pull-requests
description: Manage a GitHub PR or GitLab MR by drafting, opening, monitoring, communicating with reviewers, or handing off. Not standalone code review or deployment work.
---

# Pull requests

Treat GitHub pull requests and GitLab merge requests as the same review artifact. Use the host's vocabulary and tooling at the boundary, but apply this one lifecycle everywhere.

## Select the mode before acting

| User request | Mode | Authority |
| --- | --- | --- |
| Write, prepare, or draft a title, description, reply, or suggestion | Draft | No remote writes. |
| File, create, or open a PR/MR, including "open a draft PR/MR" | Create | Push the reviewed current branch and create one PR/MR. |
| Watch, babysit, monitor, or keep an eye on a PR/MR | Monitor | Read remote state; fix and push real in-scope defects or retry a justified flaky check. |
| Post, reply, comment, or suggest on a PR/MR | Communicate | Post that specific checked comment only. |
| Merge, close, reopen, rebase, or deploy | Separate action | Require explicit authorization for that action. |

"Draft a PR/MR" means draft the copy only. "Open a draft PR/MR" means create
the remote draft. When a request combines modes, run them in the order above.

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
uncommitted user work. After creation, report the PR/MR link, base/head, and
material review focus only.

## Monitor without scope creep

At each snapshot, record the head SHA, required-check state, mergeability, and
unresolved review items. On a later snapshot:

- Ignore a failed check tied only to an older SHA, but assess unresolved review
  feedback even when it was opened earlier.
- Inspect the current source, diff, and logs before trusting a bot or reviewer
  finding. Classify it as real and in-scope, flaky/unrelated, stale, unclear,
  or scope-expanding.
- Fix, verify, commit, and push a real in-scope defect. Retry a flaky check
  only when the request and platform allow it. Never edit product code, tests,
  CI, dependencies, or infrastructure merely to silence an unrelated failure.
- Do not turn a reviewer request into quiet scope creep. Ask whether it belongs
  in this PR/MR or follow-up work when it changes the review unit.

Do not post or resolve a human review thread solely because monitor mode is
active. Communicate mode is required for that visible action.

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
