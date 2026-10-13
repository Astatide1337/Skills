# Build stronger agents without accumulating machinery

**Adopt a lean native-first framework: keep your existing skill categories, simplify their coordination, incorporate the strongest complementary engineering methods, and add tools only when a measured capability gap justifies them.** The default should remain an agent working directly in a repository with its native search, editing, shell, browser, and project checks. P stack contributes engineering principles, Cursor’s thermonuclear review contributes structural criticism, and Ponytail contributes behavior-preserving minimalism; they should become modes of existing owners rather than three competing coordinators. Specialized tools remain project-scoped or on demand. Current tooling matters, but a recent release cannot compensate for redundant capabilities, unreliable setup, or poor results. This is a reviewable implementation and evaluation plan, not evidence that the proposed combination already outperforms your current setup. Research was checked on **October 12, 2026**; this plan installs nothing, changes no existing skills or global instructions, and authorizes no merge or deployment.

## Make the default capable before adding tools

The recommended default contains portable instructions and the capabilities already available in the active harness. It does not contain a standing MCP fleet, repository packaging, a task database, a new agent runtime, or universal scanner requirements. Your application owns build/test commands and test data. Skills owns the judgment about what to inspect, when to use those commands, and what the observations substantiate. The existing README already draws much of that distinction; preserve it rather than inventing a second execution system. ([Repository README](../README.md))

| Tier | Recommended contents | Activation and boundary |
|---|---|---|
| Default | Slim coordinator; existing engineering owners; selected P stack principles; brief correctness and Ponytail-derived minimalism checks; native project tests and harness tools | Ordinary requested implementation. Deeper thermonuclear review activates for structural changes or explicit requests; detailed references load only for the decision they address. |
| First conditional trials | Context7, Knip, axe, Serena; selected Impeccable guidance and React Doctor | Documentation, removal, accessibility, or navigation gap in a specific project. Compare against existing capabilities first. |
| Specialist conditional | ast-grep; fast-check or Hypothesis; StrykerJS; zizmor; curated Semgrep; Trivy; kubeconform; Scalene or Hyperfine | Repeated structural changes, consequential invariants, affected security/infrastructure boundary, or measured performance problem. |
| Defer | Repomix; Worktrunk; complete OpenSpec/Spec Kit/GSD/Beads/gstack/Superpowers stacks; Polaris alongside existing policy checks | Reconsider for an unmet job. Do not install multiple overlapping planning, memory, browser, scanning, or worktree systems. |

**Repomix is current, but not a daily dependency for your workflow.** Its release observed in this research was v1.18.1 on September 21, 2026. It still serves bounded export, external review, and recipients without checkout access; its own documentation says compression is generally unnecessary when incremental grep retrieval works. Your objection is therefore correct about the default use case, without requiring the claim that the project is obsolete. Worktrunk is also actively developing, with v0.80.0 observed September 27, but native harness worktrees come first. Its merge functionality must remain outside your policy. ([Repomix](https://github.com/yamadashy/repomix#available-mcp-tools), [release](https://github.com/yamadashy/repomix/releases/tag/v1.18.1), [Worktrunk release](https://github.com/max-sixty/worktrunk/releases/tag/v0.80.0))

### Route by the decision, not the size of the catalog

The framework has five layers. Personal global instructions hold durable permissions and environment facts. Project instructions and configuration hold architecture conventions, versions, commands, and acceptance recipes. `follow-instructions` selects the task path. Domain skills own specialized judgment. Optional adapters produce evidence unavailable from existing tools. Neither a leaf skill nor a tool adapter recursively initializes a second coordinator.

The normal flow is **inspect instructions and affected ownership/callers → establish expected behavior → implement a complete slice → run focused native checks and relevant acceptance actions → review correctness and unnecessary complexity → commit/push where appropriate → report observed results and gaps**. A formal plan is appropriate when requested, as here, or when consequential unresolved choices require the user’s decision. It is not an automatic gate after an implementation request.

A small formatting fix or clear one-line bug follows the short path and relevant checks. A substantial UI/API feature adds a short acceptance description, affected callers, a real journey, and framework guidance; structural review activates if ownership or interface complexity changes. An authorization repair adds causal debugging, owner/non-owner tests, and security review because the boundary demands them. A performance change starts with profiling and a frozen workload. These paths vary by evidence needed, not invented numeric thresholds for files, hypotheses, or mandatory review rounds.

Each additional specialist must answer a named question. For example, `web-interface` examines keyboard/error-state behavior while React guidance examines component lifecycle; these contributions can complement each other. Two instructions both saying “be simpler” belong in a single simplification procedure. Independent review is valuable for consequential or uncertain changes and explicit requests; it must comply with available delegation authorization and cannot be claimed without an actual returned review.

### Give review methods separate responsibilities

`code-review-and-quality` remains the correctness and readiness owner. Its structural mode incorporates thermonuclear questions about ownership, duplicated state, control flow, and unnecessary layers. `deslop` incorporates Ponytail’s preference for existing code, libraries, and platform behavior before custom machinery. Stack-specific references supply version-relevant framework constraints. `verify-work` explains what the executed checks prove. ([Thermonuclear review](https://github.com/cursor/plugins/blob/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md), [Ponytail](https://github.com/DietrichGebert/ponytail))

Produce one synthesized, severity-ranked set of actionable findings. Deduplicate by underlying defect and affected behavior, not reviewer wording. Correctness and explicit requirements outrank aesthetics. Structural critique must justify a new abstraction with an actual invariant or repeated change pattern. Minimalism must not delete validation, error handling, or authorization checks merely to reduce line count. When those methods disagree, compare the behavior and ownership of the alternatives and prefer the simpler equally correct design. Repeat review after material changes or unresolved findings, not to accumulate a fixed number of passes.

## Compose upstream strengths into the existing owners

Keep all 23 recognizable categories; most need sharper triggers and fewer obligations rather than deletion. The following is the disposition plan for the current catalog, whose names and provenance are recorded in `catalog.yaml`. ([Catalog](../catalog.yaml))

| Existing skill | Planned responsibility and change |
|---|---|
| `follow-instructions` | Slim routing and short execution path; remove ordinary mandatory HTML approval, prototype, and version-specific greenlight machinery. |
| `architect` | Ownership/interfaces; incorporate selected gstack failure-path/dataflow questions; alternatives only for a real tradeoff. |
| `code-review-and-quality` | Correctness owner; thermonuclear structural mode; risk-based independent review and integrated findings. |
| `create-workflow` | Repeated repository tasks; reuse scripts/CI before introducing workflow software. |
| `deslop` | Ponytail-derived minimalism and clutter cleanup; preserve behavior, safeguards, and scope. |
| `grilling` | Requested pressure-testing or unresolved consequential decisions; no routine interrogation. |
| `hillclimb` | Baselines, one marginal change, measured outcomes, held-outs, and removal trials. |
| `how` | Evidence-based runtime tracing; proportional inspection without compulsory artifacts. |
| `html-artifacts` | Requested/useful standalone HTML; no universal approval-medium role. |
| `internet-reach` | Source honesty and current harness adapters; label mirrors/snippets; remove hardcoded browser assumptions. |
| `production-safety` | Explicit target, live-state and recovery judgment; remove stale personal blanket approval rules. |
| `pull-requests` | Requested PR lifecycle, CI and feedback follow-through; concise repository-appropriate descriptions; never merge or deploy. |
| `security-and-hardening` | Boundary analysis, differential review, and relevant negative tests; targeted scans only. |
| `self-reflect` | Recovery after repeated failure: failed assumption, missing observation, next approach; no routine ceremony. |
| `skill-creator` | Smallest effective skill, adoption/removal evidence, dependencies, and cost accounting. |
| `systematic-debugging` | Discriminating evidence; obvious-fix short path; variant analysis when the mechanism can recur. |
| `teach` | Requested explanation fitted to reader; compose `how`/`why` as useful. |
| `unslop` | Natural prose while preserving facts; separate from code simplification. |
| `verify-work` | Evidence interpretation, native app checks, and explicit gaps; allow narrower claims from meaningful alternative evidence. |
| `web-interface` | UX, accessibility, and interactions; selective Impeccable/framework guidance and optional diagnostics. |
| `why` | Historical rationale; distinguish evidence from inferred intent. |
| `wizard` | Actual user-run setup/onboarding; not an agent prerequisite-recovery runtime. |
| `writing-for-agents` | Concise executable instruction contracts; avoid duplicated authoring rules. |

Borrow specific methods, not whole operating systems. P stack principles support ownership, causal diagnosis, and verification. gstack contributes architecture failure-path questions. Trail of Bits contributes variant analysis after a confirmed defect and meaningful property design. Impeccable contributes focused critique, clarify, harden, and adapt procedures that respect the project’s existing design system. OpenSpec contributes durable acceptance scenarios for substantial multi-session changes without requiring its entire workflow. Verify licenses and upstream revision attribution before copying text. ([gstack engineering review](https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md), [variant analysis](https://github.com/trailofbits/skills/tree/main/plugins/variant-analysis), [Impeccable](https://github.com/pbakaus/impeccable), [OpenSpec](https://github.com/Fission-AI/OpenSpec))

### Make optional capability contracts executable

For each trialed or adopted adapter, keep one small record containing its job, activation/exclusions, native alternative, evidence output, tested version/date/license/runtime, installation scope, network/credential needs, fallback, configuration owner, and rollback/removal condition. Reuse the catalog or project configuration rather than creating a registry runtime; speculative candidates need no such records. Keep metadata outside routinely loaded prompts and only actionable triggers in the skill. Use one transport per capability. Prefer a CLI behind a project command for analyzers; use MCP when an interactive semantic session genuinely helps. Context7 offers CLI and MCP routes; choose one and query the installed library version. Official docs remain the fallback. Serena should expose semantic navigation rather than duplicate file/shell tools or add another memory system. ([Context7](https://github.com/upstash/context7), [Serena](https://github.com/oraios/serena))

For Knip, calibrate framework entrypoints before accepting removals. For axe, reuse the existing browser tests and retain keyboard/manual checks. For ast-grep, use syntax matching for repeated transformations and still check behavior. Property libraries plug into the existing runner for meaningful invariants; mutation testing targets consequential modules rather than universal score targets. Security and infrastructure tools activate on affected boundaries, workflows, images, or rendered manifests. ([Knip requirements](https://knip.dev/overview/getting-started), [axe](https://github.com/dequelabs/axe-core), [ast-grep](https://github.com/ast-grep/ast-grep), [fast-check](https://fast-check.dev/docs/introduction/why-property-based/), [StrykerJS](https://stryker-mutator.io/docs/stryker-js/introduction/))

An optional tool failure should trigger a viable native fallback and an explicit evidence gap. A required project check cannot silently become optional, and a screenshot cannot substitute for interaction. Initial budget hints are no new always-on service in the baseline, one new service per pilot, and one merged review output per meaningful change. These are adjustable cost controls, not proven optimal quotas. Broad scans, RAG ingestion, database memory, paid model grading, and mutation suites remain off the ordinary path.

## Keep current versions without chasing releases

The following observed stable repository releases establish currency, not integration approval. Recheck the selected package and compatibility immediately before implementation; pin the tested compatible stable release rather than executing `@latest` during ordinary tasks. Monorepo release labels must not be mistaken for every contained package’s version.

| Candidate | Observed release and date | Recommended scope |
|---|---|---|
| Context7 | [MCP 4.3.0, Oct 9](https://github.com/upstash/context7/releases/tag/%40upstash/context7-mcp%404.3.0) | Optional documentation adapter; CLI version needs separate verification. |
| Serena | [1.7.0, Aug 9](https://github.com/oraios/serena/releases/tag/v1.7.0) | Navigation-heavy project pilot. |
| ast-grep | [0.50.0, Oct 9](https://github.com/ast-grep/ast-grep/releases/tag/0.50.0) | On-demand structural search/refactor CLI. |
| Knip | [6.41.0, Oct 9](https://github.com/webpro-nl/knip/releases/tag/knip%406.41.0) | JS/TS project command; v6 requires Node 20.19+ or Bun. |
| React Doctor | [ESLint plugin 0.9.17, Oct 5](https://github.com/millionco/react-doctor/releases/tag/eslint-plugin-react-doctor%400.9.17) | Compare unique diagnostics; this is not the CLI version. |
| Impeccable / axe | [skill 4.5.2, Oct 9](https://github.com/pbakaus/impeccable/releases/tag/skill-v4.5.2) / [4.14.0, Oct 5](https://github.com/dequelabs/axe-core/releases/tag/v4.14.0) | Selected guidance / existing browser tests. |
| fast-check / Hypothesis | [4.10.2, Sep 19](https://github.com/dubzzz/fast-check/releases/tag/v4.10.2) / [6.169.0, Oct 11](https://github.com/HypothesisWorks/hypothesis/releases/tag/v6.169.0) | One language-appropriate property library. |
| StrykerJS | [10.0.0, Aug 14](https://github.com/stryker-mutator/stryker-js/releases/tag/v10.0.0) | Targeted test-effectiveness trial. |
| Semgrep / zizmor / Trivy | [1.180.0, Oct 7](https://github.com/semgrep/semgrep/releases/tag/v1.180.0) / [1.30.1, Sep 9](https://github.com/zizmorcore/zizmor/releases/tag/v1.30.1) / [0.75.0, Oct 1](https://github.com/aquasecurity/trivy/releases/tag/v0.75.0) | Selected source rules / Actions / image and IaC checks. |
| kubeconform / Polaris | [0.8.0, Jun 4](https://github.com/yannh/kubeconform/releases/tag/v0.8.0) / [10.2.5, Sep 18](https://github.com/FairwindsOps/polaris/releases/tag/v10.2.5) | Schema checks / defer unless policy gap remains. |
| Scalene / Hyperfine | [2.3.0, May 12](https://github.com/plasma-umass/scalene/releases/tag/v2.3.0) / [2.0.0, Oct 7](https://github.com/sharkdp/hyperfine/releases/tag/v2.0.0) | Profiling and controlled timing on demand. |

Use that same integration record for maintenance. Recheck on major harness/dependency changes, security advisories, or integration failures; during active experimentation, a monthly freshness check can be useful but is not a per-task ritual. Investigate speculative candidates only when a real gap appears. Use reviewed update PRs where supported, never automatic merge or global upgrades. Old project origins do not make Hypothesis or axe obsolete. New wrappers do not earn promotion solely through release activity.

## Prove marginal value before global adoption

The constrained greedy search compares **current catalog → simplified catalog without new tools → one marginal addition**. First freeze source revisions, dirty changes, global instructions, installed hashes, model/effort, available tools, task prompt, and acceptance checks. Choose the daily model explicitly from the live catalog; the existing evaluator’s defaults must not silently select it. Existing fixtures diagnose routing and runner behavior, not superiority on real engineering. ([Evaluator](../evals/skills.py), [workflow cases](../evals/cases/workflows.json))

Start with two to four matched task pairs: **4–8 native runs**, alternating order in disposable workspaces. Select two to four task types initially from real prior work: a clear bug with unrelated dirty work, a complete feature slice, a behavior-preserving simplification, ambiguous diagnosis with recoverable prerequisites, review of known-defect and clean diffs, and version-sensitive framework work. Retain the remaining types for expansion. Freeze expectations before tuning. Review these initial outcomes before expanding. If simplification regresses quality, repair it rather than stacking tools onto the failure.

Then test at most two additions motivated by observed pain. Ranking uses marginal utility: useful new defects found, successful navigation, better accepted behavior, or reduced completion effort versus setup, false positives, latency, context, and maintenance. Quality gates are absolute: requested behavior passes, no introduced security/data-loss defect, no merge/deploy, unrelated changes preserved, no invented verification, and no unauthorized scope expansion. Speed cannot compensate for a failed gate. Record time, tokens/cost when exposed, failed calls, user interruptions, unique valid findings, missed defects, setup and maintenance. Unknown telemetry stays unknown. Prefer the simpler equal-result option; do not manufacture a universal weighted score.

Reserve untouched held-outs for a different keyboard/error-state UI journey and a boundary-sensitive change with owner/non-owner checks and a genuinely unavailable external effect. Browser acceptance must be observed through the active harness browser, not inferred from local fixture receipts. Compare promising complementary pairs where individual testing could miss synergy, and run leave-one-out trials when an earlier addition becomes redundant. A possible expanded ceiling is **24 runs**, including six baseline pairs, targeted additions, held-outs, and a few repeats/interactions; it is a ceiling, not a target. Set time/spend limits before execution. No paid grader or live evaluation was run for this plan.

### Implement in reversible phases

After design review, create an isolated branch/worktree preserving current dirty changes. Edit existing `skills/<owner>/SKILL.md` and focused `references/`; update `catalog.yaml` only when contracts/provenance change. Keep task playbooks as thin sequences linking owners. Put concrete startup, fixtures, acceptance actions, and cleanup in each application’s project-local `verify-<app>` skill or existing verification documentation. Do not invent an application CLI where native commands suffice.

Next adjust `evals/cases/` and affected `evals/tests/` expectations to remove discarded ceremony while retaining authority and evidence checks. Improve `scripts/install.sh` with explicit target selection, staged validation, local-change preservation/backup, revision receipt, executable dependency closure, idempotence, and restore/uninstall tests. Do not build an elaborate registry runtime. Before any replacement, compare unique content in `~/.agents/skills` and `~/.codex/skills`; select a canonical discovery path per harness without deleting plugin-owned names or the only copy of user edits.

Proposed later checks are `./scripts/validate-skills.sh`, `python3 -m unittest discover -s evals/tests`, and `uv run inspect list tasks evals/skills.py` in a prepared environment. Validation can resolve dependencies; these commands are **not reported as run here**. Perform model-free runner preflight for binary resolution, startup metadata, disposable permissions, and `bwrap_preflight` before native comparisons. Confirm current CLI syntax and set explicit arms, roots, model/effort, case IDs, and `include_behavior_grader=False`. An unsupported runner is unavailable evidence, not permission for an unsafe fallback. ([Validation script](../scripts/validate-skills.sh), [installer](../scripts/install.sh))

Trial accepted candidates in one relevant JS/TS and Python project if available, observing roughly 5–10 applicable uses without adding a per-task reporting ritual. Catalog promotion means adopting proven routing/guidance or making an adapter available on demand; analyzers remain project-local and services do not become always-on by implication. Promotion follows review of candidate outcomes, preserved backups, explicit target installation where needed, and effective-discovery checks. Keep personal global instructions minimal: commit/push allowed, no agent commit trailers, never merge/auto-merge/deploy, explicit Kubernetes/OpenShift context and namespace, and Rutgers login recovery. GUI sudo remains machine-specific and grouped sensibly; it does not enter the portable repo.

Roll back an addition for a quality-gate failure, significant regression, repeated false positives, broken upgrades, or startup instability. Restore the previous pin/manifest and undo only trial-owned configuration/services. Demote unused or redundant adapters after a modest observation window; do not erase shared dependencies or secrets. Removing a tool must not restore the approval bureaucracy it was meant to replace.

The review decision now is the architecture and first trial order: **simplify coordination and strengthen project verification first; compose structural review/minimalism next; trial documentation, dead-code, accessibility, or navigation adapters only against observed gaps**. Choose pilot projects and spend ceilings during the integration phase. That sequence gives you a framework whose strength comes from useful evidence and complementary judgment, with a clear mechanism for removing machinery that stops earning its place.
