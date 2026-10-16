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

When assessing an existing PR/MR, ignore superseded checks and account for
unresolved current issues. Explain a material readiness issue when it affects
the requested decision or copy; use the response format the task calls for.

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

Follow [Google's Writing good CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html)
for PR/MR titles and descriptions. Apply an explicit user format or required
repository template when present. On GitHub and GitLab, the title serves as the
CL's first line; the description serves as its body.

- Write a short, specific title in the imperative that stands on its own.
- Explain what changes and why, including context and decisions that the code
  alone would not communicate. Write for reviewers and future maintainers.
- Include relevant implementation detail, shortcomings, issue references,
  benchmarks, or design links when they help readers understand the change.
  Keep enough context in the description for it to remain useful if links expire.
- Recheck the description before submission so it describes the final change.

Use Google's published examples to guide judgment. Do not impose additional
section names, bullet counts, or a fixed narrative order.

Before publication, inspect documentation and comments in the diff as well as
code. Apply the [documentation boundary](../follow-instructions/SKILL.md#documentation-boundary).
Use the temporary task workspace freely for review notes, research, and drafts.
Include findings that affect review in the PR/MR body, and keep project docs and
source comments focused on using or maintaining the change. Leave scratch
material out of the patch. Remove only unnecessary additions from this task;
preserve existing and independently edited material.

Before a create-mode push, confirm the branch contains the intended committed
review unit. A create request does not by itself authorize committing preexisting
uncommitted user work. Inspect workflows before pushing for deployments or other
effects outside the requested delivery. After creation, report the PR/MR link
and the evidence or remaining issues needed for the user's next decision.
Inspect the final tree and diff at that head. Keep accepted, failed, skipped,
and not-run checks distinct in the handoff; a draft PR can be reviewable with
known gaps, but a skipped check is not green. If a create or push response is
uncertain, read the remote branch and PR by identity before retrying so one
request cannot create duplicate artifacts.

## Complete authorized delivery

Use for an implementation task that includes a PR/MR intended for human merge.
The outcome is the completed, verified change in a merge-ready request, not a
local commit or draft. Keep three states distinct:

- **Draft:** published work with remaining implementation, review or checks.
- **Review-ready:** coherent scope and evidence suitable for feedback; host
  approvals or integration checks may still be pending.
- **Merge-ready:** engineering acceptance is established and the host's current
  merge requirements are satisfied. This status never grants permission to merge.

1. Retain the original objective, authority and acceptance. Inspect existing
   requests, intended base, current head, host rules, required checks/approvals,
   unresolved discussions and mergeability. Discover project requirements from
   the current host/configuration; do not infer them from memory or a ready flag.
2. Complete implementation and actual affected-behavior checks. Obtain independent
   review of substantive work. Assess findings against the request; repair material
   in-scope defects and refresh affected checks/reviewer coverage. A finding or
   ordinary failing check is the next action, not a final handoff. Keep optional
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
5. Before a real interruption, retain one compact continuation record using
   [the existing checkpoint guidance](../follow-instructions/references/durable-checkpoints.md).
   On resume, inspect live head/base, checks, discussions and artifact state before
   the next action. Runtime persistence owns resumption; saving text schedules no run.
6. Read the remote state back at the final head/current target. Establish completed
   scope, affected behavior, returned independent review, resolved material findings,
   required CI, required approvals, known mergeability and non-draft state. Change
   the draft flag when appropriate and read it back. Host-accepted skipped/neutral
   checks are not executed tests; record what ran and ensure engineering acceptance
   independently covers the required outcome. Pending/unknown gates stay pending.

Honor cancellation immediately: stop further implementation and perform only
safe owned-resource shutdown within the remaining authority. A hard runtime or
quota stop may prevent even a checkpoint; preserve one when possible. Neither
state is successful completion.

For an unavailable capability/authority, essential product decision or required
human-only approval, finish independent work while authority and runtime permit,
then suspend with the exact gate, remaining objective and usable resume point.
Call this externally blocked rather than successful. A small self-imposed trial
budget is not a delivery suspension reason. Request legitimate required reviews
through the authorized host workflow; never fabricate approval or resolve a
disagreement merely to turn a status green.

Report success only when engineering completion and host merge eligibility are
established. Keep permission to merge separate: never merge, enable auto-merge or
deploy under this delivery contract. [Host draft behavior](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/changing-the-stage-of-a-pull-request)
and [branch rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
explain why a ready flag alone is insufficient; the actual project remains authoritative.

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
> gpt-5.6-terra, responding on behalf of Soham.

This lookup trusts the request's `projectId` before applying the active-team
scope. A member can target another team's project. Scope the lookup to the
authenticated team before the update.
```

Keep comments relevant to the requested review or discussion. Avoid generic
praise, vague "consider" comments, and uncertain claims presented as defects.
