# Select the agent and its reasoning budget

Use before an authorized delegation to choose the child's model and reasoning
level. The coordinator and independent code review share this procedure; their
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

## Refresh OpenCode NVIDIA inventory

For OpenCode v2.2.5, run from this checkout:

```bash
python3 skills/follow-instructions/scripts/nim-models.py
python3 skills/follow-instructions/scripts/nim-models.py --apply
opencode reload
```

The first invocation is a dry run. The helper reads NVIDIA's `/v1/models`,
rejects malformed, empty, partial or wholly deprecated inventories, and syncs
only the NVIDIA provider. Newly advertised entries stay disabled with tools
false: this catalog includes non-chat models and does not prove authenticated
callability. Existing model metadata survives refresh, including disabled tombstones.
Supported legacy model fields are translated to v2; complex legacy controls
are refused with instructions to migrate using OpenCode. Removed entries are disabled. After verifying the inherited default is available and suitable,
add `--clear-unavailable-overrides` to remove references absent from the
nondeprecated inventory. Otherwise preserve role settings and report unresolved
references; an advertised default is not proof of authenticated callability.
The helper also reads `opencode models` and keeps disabled entries for absent
built-in catalog models, because config overlays rather than replaces that catalog.
Inspect remaining overrides before dispatch: an advertised disabled entry can
still have an explicit role reference. No replacement is chosen by name or size.

Use `--probe EXACT_ADVERTISED_ID --apply` to test one advertised candidate
through OpenCode v2.2.5's supported stateless
`POST /api/experimental/generate/text` API (`opencode api --standalone`). A
subprocess-only config overlay enables the candidate for this test and sets a
64-token output bound; it never changes the on-disk config. The runtime resolves
its own live credentials, including SQLite-backed connections. The helper never
reads `opencode.db` or legacy `auth.json`. Existing `OPENCODE_CONFIG_CONTENT`
is refused for probes because it would conflict with the test overlay.

A matching text response enables that candidate on apply without claiming tool
verification. For a forced harmless tool-call check, explicitly supply an
existing secret environment variable by name with `--key-env NVIDIA_API_KEY`
alongside `--probe`; never pass the key itself as an argument. Only a matching
`ping({"value":"ok"})` response marks tools verified. No key is changed.
A requested probe failure exits nonzero and skips all config writes. A 403 means
the request was denied; it does not establish an invalid key or general model
inaccessibility. Endpoint inventory alone is not proof of callable models.
Neither text nor API tool success proves the T3 child path; verify that separately.

Apply atomically replaces the config and leaves a unique private backup beside
it, preserving the config's mode. Errors preserve the last good config. Restore
with `--restore /path/to/opencode.json.nim-backup-… --apply`, even if the current
target is corrupt, then run `opencode reload`. Restart clients if their catalog
remains cached. Target discovery honors `--config`, then `OPENCODE_CONFIG`, then `OPENCODE_CONFIG_DIR`,
then `XDG_CONFIG_HOME/opencode` (default `~/.config/opencode`). JSONC targets are
refused; when both global JSON and JSONC exist, select a JSON target explicitly
and inspect the runtime's merged settings. The helper refuses ambiguous
legacy/native NVIDIA definitions and malformed options/settings maps.

Reports list unresolved `model`, `small_model`, and `agent`/`agents` model
references to absent or disabled NIM entries; unrelated providers are preserved.
`removed_overrides` separately records explicit removals of absent NIM references.
No startup hook or scheduler is installed; invoke refresh explicitly before
model selection. Offline checks, discovered by the existing CI suite:
`uv run --frozen python -m unittest discover -s evals/tests -p test_nim_models.py -v`.

Version evidence: the [v2.2.5 NVIDIA plugin](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/core/src/plugin/provider/nvidia.ts)
adds headers, without inventory discovery. Custom providers need explicit models
([v2 providers](https://dev.opencode.ai/v2/docs/providers)); plugins can implement
inventory transforms ([server plugins](https://dev.opencode.ai/v2/docs/build/plugins/server)).
This explicit sync uses the [v2.2.5 provider schema](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/schema/src/config/provider.ts)
and installed `opencode reload` command, avoiding a persistent plugin and its
credential lifecycle. NVIDIA documents the inference endpoint in its
[LLM API reference](https://docs.api.nvidia.com/nim/reference/llm-apis).

## Match the role to the work

For ordinary delegation, prefer the least expensive capable worker available
within the user's constraints, including a smaller model from the parent's
provider or model family. A frontier orchestrator may use a smaller model at
high or maximum reasoning for bounded implementation, context gathering or
browser work when its capabilities and the task justify that setting. High
reasoning does not by itself make a smaller model a frontier model or establish
browser capability. The different-model preference and provider order below
apply only to independent code review, not ordinary workers.

Delegate bounded execution and evidence gathering by default when supported;
keep architecture, ambiguous tradeoffs, subtle-bug reasoning and final acceptance
with the frontier owner. Workers may run sequentially when their tasks depend
on one another. Keep trivial work local when dispatch costs more than doing it.

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
