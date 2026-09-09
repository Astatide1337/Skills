---
name: follow-instructions
description: Use whenever another catalog skill applies. Route skills; gate mutation, publication, and completion on evidence. Add security-and-hardening for secret-access changes. Not casual questions.
---

# Follow Instructions

Turn selected instructions into enforced prerequisites. This skill coordinates
domain skills; it never substitutes for them.

## Bootstrap before acting

Until bootstrap is complete, only read instruction sources and perform
read-only discovery needed to locate them. Do not edit, run a mutation-capable
command, create a branch or commit, publish, or claim a result.

1. Identify the requested outcome, contemplated actions, affected boundaries,
   and intended completion claim.
2. Select every skill whose own trigger matches any of those dimensions. Treat
   coverage as non-substitutable: production safety does not replace security
   review of secret access; debugging does not replace review or publication;
   PR/MR management does not prove the result it describes.
   Any proposal to copy, mount, expose, relocate, or change a consumer of
   secrets requires `security-and-hardening`, even when the same operation also
   requires `production-safety`.
3. Read every selected skill and each required reference completely.
4. Extract only obligations that can change permission, prerequisite
   inspection, required evidence, mutation scope, a stop condition, or a
   truthful completion claim.
5. Track each obligation as `pending`, `satisfied`, `not applicable`, or
   `blocked`, with its source, timing, and evidence. Unknown is not
   `not applicable`.

## Require a pre-mutation checkpoint

Before the first mutation or external write, record a compact checkpoint in a
progress update or internal scratchpad. It must contain:

- selected skills and required references read;
- exact target, environment, and authoritative source;
- relevant knowns, unknowns, and assumptions;
- the current causal or design hypothesis, at least one plausible alternative,
  and the observed check that discriminates between them when causality matters;
- affected owners, consumers, identities, writers or controllers, and
  sensitive data;
- the proposed change, rollback, and its complete effect path;
- evidence required before publication and completion.

For a relevant multi-process or multi-container boundary, include:

| Owner | Process | Input | Filesystem or API boundary | Sensitive data |
|---|---|---|---|---|

Do not mutate while a required checkpoint field is blank or inferred. Keep the
full ledger internal unless it blocks progress, instructions conflict, the user
requests an audit, or a missed obligation requires disclosure.

## Cross the gates in order

### 1. Inspection

Inspect the exact target, owning implementation, authoritative configuration,
and every relevant process, filesystem, identity, controller, or API boundary.
Separate observation from assumption. An error message proves a symptom, not
its cause.

### 2. Causality or design

When the task changes behavior, compare plausible explanations or ownership
layers and run the smallest check that distinguishes them. Connect the proposed
change to the observed mechanism. Stop if the owning implementation or material
runtime boundary remains uninspected.

### 3. Mutation

Confirm exact authorization, scope, affected consumers and sensitive data,
competing writers or reconciliation where relevant, and rollback. Re-read the
selected skills' mutation and stop conditions.

Trace the effect path explicitly:

`edited source or desired state -> build/render/reconciliation -> deployed consumer -> requested behavior`

Choose the narrowest authorized layer whose available path reaches the target.
A source edit is not a fix for an existing artifact when an unavailable or
unperformed build, publish, reconciliation, or rollout is still required. Do
not broaden secret access to resolve path, mount, identity, or ownership
uncertainty.

When a sensitive producer already exposes its owned directory to the intended
consumer, configure the consumer to read the exact required file there. Do not
copy or alias-mount the whole sensitive bundle under a legacy consumer path
unless the consumer cannot be configured directly and the broader path exposure
has been justified and verified. Prefer changing a configurable command or
configuration pointer over duplicating producer-owned secret paths.

For an orchestrated workload, decide explicitly whether the owning change is in
the deployment's command/arguments, generated configuration, or image. If the
current task has no authorized and available image build, publish, and rollout
path, editing a Dockerfile or image entrypoint fails the effect-path gate. When
the consumer accepts the needed path as a startup argument and the orchestrator
supports a command or argument override, prefer that scoped desired-state
change over rebuilding the image or remounting a producer-owned secret bundle.

### 4. Publication

Before committing, pushing, opening or updating a PR/MR, commenting, or
deploying, inspect the complete final diff and satisfy every applicable
correctness, architecture, security, operational, and authorization obligation.
Ensure the description states the established mechanism and no unresolved
assumption as fact. Structural validation proves only structure.

### 5. Completion

Name the requested observable result and require current evidence at that
layer. State material unknowns and narrow the claim accordingly. A green build,
valid manifest, successful command, or healthy controller does not substitute
for runtime behavior.

For a completed sensitive multi-process change, report the competing
explanations distinguished, the resulting owner/process/input/boundary/secret
map, and the evidence that access did not broaden. Do not hide a missing gate
behind a concise handoff.

Audit that report before the completion claim. If it omits the alternative
hypothesis and discriminating result, the boundary map, the end-to-end effect
path, or a material runtime limitation, the completion gate remains pending.
Use this compact evidence shape so the obligations remain observable:

- `Alternatives tested:` each material hypothesis and the observation that
  distinguished it;
- `Boundary map:` one row per relevant owner or process, naming input,
  filesystem/API boundary, and sensitive data access; and
- `Effect and evidence:` changed source or desired state through its consumer
  and requested behavior, followed by static, runtime, and publication limits.

Prefer an existing mechanical check when it directly tests an obligation. Do
not invent automation merely to avoid a bounded judgment call.

## Recover from a missed obligation

If a prerequisite was skipped, stop further mutation, name the omission and
risk, inspect whether existing work is unsafe or misleading, and disclose the
mistake when it affected the work or claim. Revert, revise, or continue only
within existing authorization. Add a deterministic check when it can reliably
replace the failed judgment. Do not defend the result because later evidence
partially supports it.
