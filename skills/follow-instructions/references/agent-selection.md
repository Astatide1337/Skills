# Select the agent and its reasoning budget

Use before an authorized delegation to choose the child's model and reasoning
level. The coordinator, PR review and Better Call Sol share this procedure; their
own rules still determine scope, acceptance and whether review is required.
Keep the parent model, global settings, keys, quota and permissions unchanged.

## Discover before choosing

1. Preserve explicit provider, model, effort, speed and spending constraints.
   Use a configured role preference when one exists. Otherwise select from the
   available coding-capable models for this task.
2. Inspect the current runtime. In T3, call `orchestrator_capabilities` once
   before the first `delegate_task`; repeat only after an error or a user-named
   provider change. Take model IDs and effort keys/values from that result, never
   from memory or an earlier session. A truncated catalog is not evidence of
   absence: use its documented search.
3. Keep two facts apart. *Tooling availability*: the provider is enabled, can
   run the child, and exposes the tools the role needs (shell, browser, edit).
   *Model capability*: the exact model supports tool calling, image input and
   the effort option the role needs. A catalog listing proves neither; verify
   from advertised capabilities or a minimal probe on the actual child path.
4. Choose role, difficulty and needed evidence before the model. Record the
   provider, model, effort and reason in the brief, plus the runtime's returned
   selection; never claim requested settings were used when the runtime reports
   otherwise.

## Match the role to the work

| Work | Starting capability and reasoning | Raise effort when |
| --- | --- | --- |
| Context gathering, file reading, inventory, history lookup | Efficient model with reliable tool use; low | Evidence conflicts or the result drives a consequential decision |
| Browser or user-flow testing | Economical model with verified tool use and image input; low or medium | A flow fails ambiguously; re-run with the frontier model only for the disputed observation |
| Ordinary implementation with established interfaces | Capable coding model; medium | Root cause, compatibility or ownership remains uncertain |
| Architecture, subtle concurrency, security/data boundaries, failed premise | Frontier model; high | A specific unresolved interaction needs deeper analysis; xhigh only if supported and justified |
| Independent review | Frontier or strong code model, different from the implementer ([below](#independent-review-model)); high for material changes, medium for narrow ones | A failure spanning several components remains unexamined |
| Prose, visual taste and synthesis | Judgment model; medium with actual examples/artifacts | Conflicting requirements or consequential ambiguity remains |
| Baseline/candidate experiment | The same frozen model and effort in both arms | Never change one arm mid-comparison |

Context and browser roles supply observations; they do not own conclusions. The
frontier owner decides architecture and subtle-bug questions and opens the raw
source behind any claim such a child cites before relying on it. Use project
preferences or measured results for comparable tasks when available; model
names alone do not establish capability. Do not select an image, audio or
embedding model merely because a provider lists it.

Use standard speed by default. A faster/priority setting needs explicit authority
and a real latency benefit; reasoning level is not a service tier. Do not default
to maximum effort or multiply reviewers to compensate for a vague brief. After a
repeated failure, improve the evidence or narrow the unit before raising effort.
Honor a user's exact effort and budget.

## Independent review model

Unless the user names a reviewer, the reviewer's model differs from the model
that wrote the change. Choose the first available option, in order, whose model
is not the implementer's:

1. a Claude model;
2. an OpenCode free model;
3. an OpenCode NVIDIA NIM model.

Within a tier prefer a different model family from the implementer's. Each
candidate must pass the tooling and capability check above for a reviewer
(repository read, shell). Resolve the concrete model and effort from the
runtime for each tier. If no tier offers a different model, or the user's usage
for every different-model option is exhausted, a fresh same-model reviewer is
allowed; record the reason. Preserve repository data restrictions when selecting a hosted provider; skip a
tier that cannot satisfy them. Do not change provider retention settings. Generic review does not require Sol. An explicit
user-named reviewer overrides this order and is never substituted.

## Fallback on failure

For independent review, this order is standing authorization: when a candidate fails with quota,
rate-limit, usage-exhausted, provider-disabled or lacks-capability errors, move
to the next candidate without asking again. Record each attempt (provider,
model, failure class) and the model finally used. Fallback never crosses the
user's explicit constraints, widens permissions or changes global settings. A
failure caused by the task itself (a crash, bad brief, failed check) is not a
reason to change model: fix the brief or narrow the unit. After exhausting different-model options, try the permitted fresh same-model
reviewer. For other roles, choose an available model with the required capability
under the user's cost and provider constraints, rather than applying reviewer
tiers blindly. If no capable worker remains, continue safe parent-owned work.
If independent review remains unavailable, report it pending; self-review is not
independent review.

## Dispatch through the supported runtime

Use native children for same-provider, supported-model work with no extra
settings that finishes in this turn, as required by the host. Use T3
`delegate_task` for cross-provider work, requested settings, background work or
an isolated checkout. Do not create top-level threads to simulate children, and
do not build a CLI wrapper, polling scheduler or shell-created child checkout.
Only the parent orchestrator dispatches; a child never starts children.

In T3, pass model and provider in `target`, and reasoning in `target.options`
using the advertised key and value. Do not invent a model suffix or option name.
Preserve unrelated settings. Omit `runtimeMode` unless supervision was requested;
an approval mode is not read-only isolation. Put the child's permitted effects
in its brief and use real runtime isolation when required.

`isolation: "worktree"` starts from the parent commit and excludes uncommitted
edits. Commit the integrated changes or use another supported transfer before asking
that child to verify them. Identify uncommitted and untracked changes explicitly;
the checkout name or a head SHA alone does not prove it contains them.

Every new independent review or recheck gets a fresh task and brief. Keep task
ID, returned artifact/revision, actual settings, pending questions and verdict
in the existing record. Follow the task's returned `next` instruction;
completion wakes and PR watches replace polling. Cancel a superseded worker with
task cancellation, not an interrupt on its underlying thread. Before using a
late result, confirm it still matches the assigned work and current revision.

If an explicitly requested model/provider is unavailable, report it and continue
independent work; do not silently substitute. A timeout does not cancel a child;
follow its live return contract.
