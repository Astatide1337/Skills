# Full contract template and grammar

Use when drafting a full spec or interpreting validator errors. Replace the
example content below with concrete answers, or justified non-applicability
where a field allows prose. This grammar checks structure, not the answers.

Use these twelve exact `##` headings once, in order. Each section must contain
nonempty unfenced body content; bare list markers, horizontal rules, HTML
comments and headings alone do not count. Ordinary Markdown prose, lists, links and subheadings
are allowed. Backtick and tilde fenced examples are ignored, including apparent
headings, fields, declarations and references inside them.

Metadata is `Label: value`, optionally preceded by `-`, `+` or `*` and whitespace.
Required metadata appears exactly once in its shown section: Spec, Revision,
Owner; Assigned; Score, Assessor, Basis, Uncertainty, Next evidence. Score is a
base-ten integer from 1 through 10, never a boolean or fraction.

Declarations are single lines, optionally unordered list items:
`R-01: key=value | key=value`. A declaration starts with an ID immediately
followed by a colon; an ID followed by ordinary prose is not a declaration.
IDs are R-, A-, or AC- followed by at least two
ASCII decimal digits. Declare each ID once in its owning section. Fields must
be nonempty; keys are exact, required, unordered and unique. Literal pipes in
values are unsupported; use prose continuation outside the declaration instead.

- R fields: condition, behavior, source, acceptance, assumptions.
- A fields: claim, status, evidence, consequence, next, owner, affects.
- AC fields: requirements, check, expected, evidence.

Declare at least one R and AC. If no assumptions apply, explain why in prose.
Status is verified, refuted or unresolved. Unresolved/refuted declarations emit
diagnostics with affected requirements and evidence, without failing structure.

Explicit `@R-01`, `@A-01`, `@AC-01` tokens reference declarations; plain mentions
are prose. All explicit references outside fences must resolve. Reference-list
fields use whitespace/comma-separated tokens: R.acceptance requires AC tokens;
R.assumptions uses A tokens or `none`; A.affects and AC.requirements require R
tokens. Links must be reciprocal in both directions. Assigned uses R tokens or
`none`. Reserved declaration/reference prefixes with malformed IDs are errors.
Text in all other fields is free wording, including inline Markdown.

The example is a valid unresolved planning draft, not a completed acceptance
report. Copy its contents without the surrounding fence:

```markdown
## GOAL / OUTPUTS
Spec: PERSONAL-ADAPTER
Revision: 1
Owner: integrating agent
Deliver a local adapter in the personal repository; remote rollout excluded.

## INPUTS
Original request and inspected caller at recorded base/head; identify fixtures
and runtime. Separate source observations from prior reports.

## SCOPE
Local adapter behavior and compatibility; no remote settings or deployment.

## AUTHORITY
Reference the actual authorization, permitted effects, remaining budget and
separate merge/deploy decisions. Full access does not expand task authority.

## REQUIREMENTS
R-01: condition=when remote verification is available | behavior=verify adapter compatibility | source=accepted request | acceptance=@AC-01 | assumptions=@A-01

## DESIGN
Use the existing adapter owner/interface; describe normal call, failure and
recovery without a new service. Explain any material alternative.

## ASSUMPTIONS / DISCOVERY
A-01: claim=remote verification can run | status=unresolved | evidence=prior report only | consequence=remote completion cannot be claimed | next=inspect host prerequisites within authority | owner=integrating agent | affects=@R-01

## EXECUTION / ORCHESTRATION
Assigned: @R-01
Use the single Orchestration definition in follow-instructions/references/approved-plans.md.
Record dependency-ordered tasks with R/A links, host/capabilities, workspace,
ownership and review responsibility there; state a concrete reason if no workers.

## STATE / CONTINUATION
Record observed target-system conditions on which requirements depend. Retain
progress, failures, revision and next action in the native task record. For a
remote reader without access, provide a minimal authorized snapshot via an
accessible branch/attachment or brief, identify source/revision and verify
access. One-session work needs no extra progress file.

## VERIFICATION / ACCEPTANCE
AC-01: requirements=@R-01 | check=existing compatibility command plus invalid-input case | expected=supported input works and invalid input fails safely | evidence=planned command output tied to artifact revision
Keep planned checks distinct from passed/failed/not-run/blocked observations.

## STOPPING
Complete only after acceptance evidence is inspected. Remote claims remain
blocked pending A-01; independent authorized local work can proceed. Preserve
unfinished checks and owner after failure/interruption.

## CONFIDENCE
Score: 6
Assessor: integrating agent for revision 1
Basis: local caller inspected; compatibility check identified
Uncertainty: remote runtime prerequisites unverified
Next evidence: bounded host prerequisite observation
```

The EXECUTION / ORCHESTRATION section uses the existing
[Orchestration definition](../../follow-instructions/references/approved-plans.md#establish-the-decision).
Do not maintain a second definition here. For design judgment use
[architect](../../architect/SKILL.md); for instruction prose use
[writing-for-agents](../../writing-for-agents/SKILL.md).
