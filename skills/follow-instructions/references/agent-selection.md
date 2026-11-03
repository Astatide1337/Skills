# Select the agent and its reasoning budget

Use before an authorized delegation to choose the child's model and reasoning
level. The coordinator, PR review and Better Call Sol share this procedure; their
own rules still determine scope, acceptance and whether review is required.
Keep the parent model, global settings, quota and permissions unchanged.

## Discover before choosing

1. Preserve explicit provider, model, effort, speed and spending constraints.
   Use a configured role preference when one exists. Otherwise select from the
   available coding-capable models for this task; a catalog listing alone is not
   evidence that an arbitrary model supports tools or the requested workload.
2. Inspect the current runtime capabilities. In T3, call
   `orchestrator_capabilities` once before the first `delegate_task`; repeat only
   after an error or a user-named provider change. Check the provider is enabled,
   can run the child, and advertises the exact model and options. A truncated
   catalog is not evidence of absence: use its documented search when needed.
3. Choose the role, difficulty and evidence needed before the model. Record the
   exact provider, model, reasoning option/value and why they fit this task in
   the existing brief. Defaults below are starting choices, not benchmark claims.
   Record the selection returned by the runtime; never claim requested settings
   were used when the runtime reports otherwise.

## Match the role to the work

| Work | Starting capability and reasoning | Raise effort when |
| --- | --- | --- |
| Bounded lookup, inventory or mechanical edit with a clear check | Efficient coding/research model; low or medium | Evidence conflicts or the edit has consequential behavior |
| Ordinary implementation and maintenance with established interfaces | Capable coding model; medium | Root cause, compatibility or ownership remains uncertain |
| Architecture, subtle concurrency, security/data boundaries or a failed premise | Strong code/judgment model; high | A specific unresolved interaction needs deeper analysis; use xhigh only if supported and justified |
| Independent review | Capable code reviewer; high for material changes, medium for narrow changes | A failure spanning several components remains unexamined |
| Prose, visual taste and synthesis | Judgment model; medium with actual examples/artifacts | Conflicting requirements or consequential ambiguity remains |
| Baseline/candidate experiment | The same frozen model and effort in both arms | Never change one arm mid-comparison; model changes are a separate experiment |

Resolve model IDs and supported effort values from the active runtime. Use
project preferences or measured results for comparable tasks when available;
model names alone do not establish capability. Do not select an image, audio
or embedding model merely because a provider lists it.

Prefer a different model family for independent review of consequential work
when authorized and available. A fresh same-family reviewer still counts as
independent review unless the user requires diversity. Agreement is not proof:
reviewers inspect requirements, the actual candidate, callers and raw checks.

Use standard speed by default. A faster/priority setting needs explicit authority
and a real latency benefit; do not equate reasoning level with service tier.
Do not default to maximum effort or multiply reviewers to compensate for a vague
brief. After a repeated failure, improve the evidence or narrow the unit before
raising effort. Honor a user's exact effort and budget rather than raising them.

## Dispatch through the supported runtime

Use native children for same-provider, supported-model work with no extra settings
that finishes in this turn, as required by the host. Use T3 `delegate_task` for
cross-provider work, requested settings, background work or an isolated checkout.
Do not create top-level threads to simulate children. Do not build a CLI wrapper,
polling scheduler or a shell-created child checkout.

In T3, pass model and provider in `target`, and reasoning in `target.options` using
the advertised key and value. Do not invent a model suffix or option name.
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
independent work; do not silently substitute or call self-review independent.
Generic review can select an available reviewer before dispatch without
requiring Sol. If a dispatch fails, do not try different providers, models,
native tools or CLIs as an unasked fallback. Recheck the runtime capability and
report which required action remains pending. A timeout does not cancel a child;
follow its live return contract.
