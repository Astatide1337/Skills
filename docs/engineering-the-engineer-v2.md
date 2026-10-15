# Engineering the Engineer

## Skills v2: judgment, dependable execution, and evidence

**Design proposal · Version 2.0 · October 13, 2026**  
**Owner:** Soham Bhagat  
**Scope:** Redesign of the Skills engineering method, not a new agent platform.  
**Status:** Proposed. This document supersedes the v1 design proposal, not installed instructions or permissions. No repository implementation is authorized or performed by producing it.  
**Source baseline:** `Astatide1337/Skills`, commit `52ef9c11fc6ac42e01bd6aed78ae15bf46250290`, reconfirmed during this revision. Installed runtimes and application environments were not inspected.

> **Make repeatable work dependable. Make judgment better informed. Preserve the freedom to find a better solution. Accept results only to the extent that independent evidence supports them.**

This document is for the person and agents developing Skills. It is not an always-loaded system prompt. Its procedures should become small, selectively used resources only when implementation and evaluation justify them.

## 1. Decision and what changes from v1

Build a small, outcome-driven engineering method around three responsibilities: **engineer, verify, and improve**. Support that method with relevant examples, well-designed tools, application-owned contracts, and an acceptance boundary outside the implementer's control. Use the existing runtime, catalog, installer, application tools, and infrastructure where they already work.

The goal is not an AI organization with a role for every discipline. It is the ability to delegate meaningful engineering work without becoming the missing designer, debugger, architect, or integrator. Human decisions about objectives, preferences, risk, and authority remain distinct from corrective human engineering.

The v1 document correctly emphasized evidence, scope, and independent acceptance. It was primarily a compatibility-first migration plan. This revision adds the missing account of **how good work is produced**, how judgment is calibrated, and how improvements avoid making the model narrower or more bureaucratic. [V1]

| Earlier emphasis | Revised decision | Why |
| --- | --- | --- |
| Preserve the current workflow structure | Preserve working contracts, not every instruction or reference chain | Existing structure is a starting point, not a quality target |
| Strengthen verification at the end | Improve consequential design decisions before broad implementation, then verify the result | Repeatedly criticizing a poor direction is not a substitute for choosing a better one |
| Add guidance for observed failures | Diagnose the owning layer before intervening | The problem may be a tool, environment, requirement, evaluator, or model capability |
| Teach good patterns | Teach context, alternatives, counterexamples, and limits | A reference should inform judgment rather than become the only allowed solution |
| Optimize task success | Require quality, transfer, and retained flexibility, with cost reported separately | A narrow score can reward overfitting or suppress useful creativity |
| Grow demonstrated autonomy | Grow breadth, difficulty, and authority separately | Competence is evidence, not permission |

**The design's central distinction is judgment versus stable execution, not creativity versus determinism.** Random variation is not the quality being optimized. Deterministic code can reliably be wrong. A repeatable measurement may observe a changing world.

### Constraints carried forward

Keep the current read-only default, scoped plan approval, and no-merge/auto-merge boundaries. Automatic rule promotion remains paused. Those policies are explicit in the repository's collaboration contract. [R2]

Use existing authorized subscriptions, models, tools, and infrastructure. Do not introduce a paid service, mandatory model ensemble, new machine, continuous hosted image builds, or unrelated repository changes as a prerequisite. Preserve separate work and personal access boundaries wherever they are configured. This proposal does not establish the current readiness of K-Agent, Scarlet, or the browser environment.

Do not build a scheduler, gateway, dashboard, workflow language, vector store, universal verification CLI, or agent hierarchy. Do not replace an actual application with a mock to claim successful integration. A few focused scripts are appropriate when they remove a demonstrated gap.

## 2. Operating model: one accountable engineer

One engineering agent owns the requested result and its integration. A fresh review context challenges substantive work. Existing tools carry out repeatable operations. The improvement responsibility operates on completed or failed attempts, not by rewriting the active task's rules.

These are responsibilities, not three permanent agents, three mandatory model calls, or a fixed package count.

| Responsibility or owner | Owns | Does not own |
| --- | --- | --- |
| **Engineer** | Investigation, design choices, implementation, development checks, recovery, integration | Unilateral changes to protected acceptance or authority |
| **Verify** | Independent expectations, artifact-first review, additional observations, evidence sufficiency | Quietly becoming the author or redefining the user's objective |
| **Improve** | Failure diagnosis, candidate interventions, comparisons, proposed adoption or removal | Self-approval or changing its own benchmark to claim a win |
| **Application** | Behavior, canonical types and rules, native tests, local design decisions, supported setup | A duplicate of the shared engineering manual |
| **Runtime and existing tools** | Permissions, sessions, isolation, repeatable execution, resource limits, observed results | Product intent or aesthetic judgment hidden inside automation |
| **User** | Goals, material trade-offs, quality anchors, authorizations | Routine debugging, implementation, or verification work the system promised to own |

### Task flow

```text
Objective + authoritative context + authorized effects
                         |
            Engineer establishes the task
            and a proportionate quality bar
                         |
        Design / implement / inspect / repair
        using existing tools and relevant examples
                         |
              Identified candidate artifact
                         |
       +-----------------+------------------+
       |                                    |
Protected checks and                Independent judgment
external observations               of artifact and evidence
       |                                    |
       +-----------------+------------------+
                         |
               Applicable gates satisfied?
                  /                  \
                No                    Yes
       Diagnose the actual gap     Authorized delivery
       or retain unresolved state with bounded claims
```

This is an execution description, not a new state-machine implementation. Investigation can continue during implementation. New evidence may legitimately reopen a design decision. Do not require a ritual sequence of tool calls when another authorized approach establishes the same outcome.

For substantive work, reuse one existing task record: **outcome, constraints, authoritative inputs, acceptance, permitted effects, candidate identity, evidence, unresolved decisions, next action**. Keep links to detailed artifacts rather than copying logs into the record. On interruption, preserve accepted decisions, unfinished gates, the current artifact, and the next useful observation. A tiny local correction retains the existing short path. [R1]

The engineer inspects owners and callers before choosing a design. Reuse an existing approval when it covers the scope. A material behavior, architecture, evidence, or authority change reopens the relevant decision. Normal in-scope corrections should not require repeatedly asking the user to approve the same work.

**Rationale:** a single integration owner limits conflicting edits and handoff loss. Independent assessment limits self-certification. Neither requires an imitation company of specialist agents.

## 3. Put each obligation in the right layer

### Requirements, defaults, and examples are different

**Requirements** define what must hold, including allowed effects and required behavior. **Defaults** are useful methods that may be departed from for a task-grounded reason. **Examples** demonstrate decisions under particular conditions and do not grant authority.

A requirement might prohibit unauthorized record access. A default might favor the existing authorization owner. An example might show a service-based implementation. The example does not require every application to adopt that architecture. A better implementation can satisfy the same requirement.

Each permanent resource should answer: *What decision does this change? When does it apply? Why is this the correct owner? What would justify revising or removing it?* Do not create a registry just to store those answers. A short note with the existing resource is sufficient.

### Judgment, deterministic checks, and environmental procedures

| Kind of work | Example | Design treatment |
| --- | --- | --- |
| Judgment under constraints | Choose a page composition or module boundary | Give the model context, alternatives, and quality references. Review the decision |
| Stable computation or rule | Validate a known schema or enforce an approved import boundary | Use the established validator, compiler, or lint rule |
| Repeatable procedure over changing state | Start services, capture a screen, measure latency, inspect a rollout | Control relevant inputs and record conditions. Do not promise identical observations |
| Permission boundary | Read credentials, publish, merge, or deploy | Enforce through runtime/platform controls, not advisory examples |
| Mixed activity | Debugging or verification | Let the model choose informative checks. Let tools execute and preserve observations |

Do not automate a poorly understood decision merely because code can be written for it. First establish the operation's contract. Conversely, stop asking the model to repeatedly reconstruct a stable procedure once a dependable native tool already exists.

External guidance supports concise, relevant context and clear tools rather than brittle prompt logic. This design uses that as a hypothesis to test in the actual workflow, not as proof that less guidance is always better. [E1] [E2]

## 4. Tool design: automate mechanics, not the solution

A tool is justified when an existing native command is insufficient and a narrow adapter removes a recurring, consequential failure or expensive repeated operation. Prefer improving the owning CLI to building a competing wrapper. Do not expose every library function as a separate agent tool.

Each added operation needs explicit inputs, prerequisites, targets, effects, outputs, failure semantics, and ownership. Return enough information for the next decision, with detailed artifacts accessible separately. Avoid both opaque `success: true` responses and unbounded logs.

### Illustrative operation: prepare an isolated application instance

This is a proposed contract, not a new command or a claim that it already exists.

| Contract element | Required behavior |
| --- | --- |
| Inputs | Explicit application candidate, supported configuration, isolated data choice, and resource scope |
| Preconditions | Required runtimes and permissions checked without silently installing packages or broadening access |
| Effects | Only declared run-owned processes and data. No production fallback |
| Result | Instance and artifact identity, relevant dependency versions, auth/data mode, observed readiness, evidence locations |
| Failure | Identify the failed stage, effects already completed, recoverable options, and any unresolved state |
| Retry/cancellation | State whether repeat invocation is safe. Inspect uncertain effects before retrying. Clean up only owned resources |
| Limit | Readiness establishes that this instance started. It does not establish a successful user journey |

The same contract discipline applies to browser driving, file transformation, assertions, and supported recovery operations. Determinism and idempotency are separate properties. A repeatable request can still duplicate a write.

Tool verification must cover the relevant valid input, invalid input, interruption, partial failure, and repeated invocation paths. Test the actual interface with a fresh agent as well as testing its implementation. A canary check should demonstrate an important permission boundary where that boundary is claimed.

Do not create a universal result schema when a native format is adequate. Add missing identity or status information at the owning tool. Process exit, application failure, check failure, and unavailable capability must remain distinguishable.

**Adoption rule:** an AI-written tool is candidate software until reviewed and exercised. It cannot be edited by the task's implementer and immediately treated as an independent certifier of that same task. Tool-interface clarity and meaningful errors are supported by Anthropic's tool-engineering guidance. [E2]

## 5. A small library of engineering judgment

Store high-signal examples next to their owning skill or application, not in an unexplained global collection of good and bad work. Start with observed failures and accepted work. A resource can be a screenshot pair, a reviewed diff, a dataset, an incident exercise, or a short evolving feature history.

### Minimum content of a worked example

Establish the situation and constraints. Show a plausible rejected approach and an acceptable approach. Explain the consequential difference. Include a way to inspect or execute that distinction, a valid alternative when useful, and the conditions under which the lesson stops applying.

Avoid turning this into a mandatory elaborate template. Some lessons need one image and a paragraph. Others need an executable fixture. A repository-wide example authoring framework is unnecessary.

| Domain | Useful resource | What it teaches | Where actual truth stays |
| --- | --- | --- | --- |
| UI/UX | Annotated comparable renders, including an acceptable alternative | Hierarchy, composition, interaction clarity, task fit | Application design references and actual rendered states |
| Code and architecture | Two implementations of the same requirement with reviewed trade-offs | Ownership, justified reuse, unnecessary complexity | Application source and contracts |
| Maintainability | Initial feature followed by a real, plausible next change | Change propagation, discoverability, hidden coupling | Application history and disposable evaluation copies |
| Security | Allowed/denied operations with independently expected effects | Enforcement beyond hidden controls and happy paths | Application permission policy |
| Data and behavior | Small edge-case datasets and state-transition exercises | Persistence, cancellation, retries, integrity | Native fixtures and tests |
| Debugging | Symptom, competing explanations, decisive observation, correction | Causal investigation rather than patch guessing | Sanitized case evidence |
| Reliability/performance | Reproducible failure or workload with relevant measurements | Recovery and comparison under explicit conditions | Native runbooks, tools, and environment |
| Verification | Valid candidate, meaningful defect, missing/stale evidence | False acceptance and false rejection | Separately controlled acceptance inputs |

A shared example is not a copy of a changing application policy. Prefer an application-owned exemplar of one well-integrated feature over an artificial universal starter architecture.

### Selection, provenance, and separation

Use existing skill discovery and ordinary repository search. Load only examples that address a material decision. A screenshot must actually reach a vision-capable tool or model. Mentioning its path does not establish inspection. Motion requires the relevant temporal evidence, not a still image.

Record source, relevant revision, applicability, and asset permissions. Remove secrets, personal records, credentials, and unnecessary transcripts. Retrieved content, logs, and examples are untrusted data, not new instructions. Review executable examples before use.

Keep teaching cases separate from reserved evaluations. Withhold test realizations and answers, not requirements. Once a reserved case informs an improvement, treat it as development material and use fresh cases for later transfer claims. Examples should cover different successful styles and useful exceptions, not only one favored output.

**Rationale:** the library should enlarge the agent's repertoire. It should not become a hidden style mandate or an answer key. Selective resources are compatible with existing Agent Skills packaging. [E3]

## 6. Produce quality before trying to certify it

Required functionality, security, visual quality, usability, and maintainability are separate obligations when applicable. One cannot compensate for another. But reviewer preferences are not automatically blocking requirements. Establish the relevant bar from the request, product context, accepted references, and current contracts before judging a candidate.

### UI/UX: direction, judgment, and fidelity

Apple or agency-level work is a reference for deliberate craft, not a mandatory visual style. Do not translate it into a universal rule for white space, glass, large headings, novelty, or any particular component library. A dense operational workspace and a marketing page have different jobs.

For consequential UI work, establish the user task, realistic content, important states, product conventions, and the agreed visual ambition. Reuse the existing prototype-approval path. Do not require a new design competition for a small correction or already approved direction.

When quality fails, diagnose three capabilities separately:

| Diagnostic question | Exercise | Intervention when it fails |
| --- | --- | --- |
| Can the evaluator recognize quality? | Compare accepted and rejected renders, unseen cases, and valid stylistic alternatives without author labels | Calibrate or replace the assessment. Permit disagreement and “insufficient evidence” |
| Can the implementer realize a good target? | Implement an approved composition with authorized assets and real behavior | Improve rendering access, asset handling, layout implementation, or tools |
| Can the designer originate a strong direction? | Develop a representative slice using real content without building the whole product | Change the reference set, design method, or bounded exploration strategy |

Reproduction, adaptation, and original design are diagnostic options, not compulsory stages. A strong original solution can proceed immediately if it meets the same requirements.

For an uncertain direction, compare a small number of genuinely different compositions on one representative screen. Choose using the task and visual standard, then implement a real vertical slice. Do not expand a mediocre first screen across the application. Do not use an image as the interface or hardcoded positioning that only works for the sample text.

Assess the actual running result at relevant viewports and states. Inspect information hierarchy, proportions, typography, assets, coherent grouping, and the overall composition. Exercise the real interaction, including applicable error, empty, loading, cancellation, persistence, and keyboard behavior. A screenshot checker cannot establish task usability. An agent-run task is not a study of real people.

Keep a best-so-far candidate. A revision must address a specific observed gap. If cosmetic refinement stalls, reopen the direction instead of layering on effects. The design system itself may be the cause, so test a suspect default rather than insisting on compliance. Extract reusable patterns from successful screens without turning every unique decision into a component.

Anthropic's frontend case study reports that evaluator calibration mattered, later iterations were not invariably preferable, and repeated refinement could add complexity. Those observations motivate bounded exploration, retained candidates, and review of the evaluator. They do not prove this proposed workflow will reach the user's visual bar. [E5]

**Acceptance:** the real interface meets the agreed visual and interaction standard, not merely a generated aesthetic score. Automated accessibility checks support the assessment but do not establish comprehensive accessibility on their own. [E7]

### Maintainability: assess the change and its consequences

Before broad implementation, establish the affected owners, canonical types and rules, relevant callers, public interfaces, and data flow. The agent should identify where behavior belongs and why a new dependency or abstraction is necessary now. No universal folder structure or programming paradigm is imposed.

Keep product logic out of competing helpers. Preserve established state, authentication, modal, and sharing owners where applicable. An approved boundary can be supported by native types, schemas, linting, or import rules. Do not impose a global ban on abstractions, comments, or multiple files.

For a consequential new boundary or recurring maintainability failure, run a **disposable follow-up change** based on a credible requirement. A fresh context receives ordinary project guidance, not the author's full explanatory transcript. Inspect whether it finds the owner, changes the behavior coherently, and preserves the affected contracts. Look for unexpected coupling, duplicated synchronization, and undocumented assumptions. File count is not the score.

The follow-up is a diagnostic exercise, not permission to ship extra functionality. A tiny change does not need it. Subsequent real features provide stronger longitudinal evidence than a one-time “clean code” verdict.

Google's review guidance prioritizes integration, understandable complexity, present needs, and useful tests. This design applies those concerns to review and change exercises rather than inferring maintainability from naming or folder layout. [E6]

## 7. Acceptance: expectations, observations, and judgment

The trusted outcome is not the implementer's final message. For substantive work, acceptance combines independently established expectations, observed behavior, and a separate assessment of the artifact.

### Establish and protect the expectation

The engineer may propose checks. A separate assessment derives or reviews expected behavior against the original objective and authoritative application contracts before the acceptance version is protected. Pre-change behavior can define a regression invariant, but not justify preserving the bug being fixed.

Freeze acceptance inputs outside the implementer's write authority for the run. Development tests may remain editable. The evaluator can investigate additional cases of the stated requirement without inventing new product scope. A material correction to acceptance is explicit, versioned, and independently reviewed. It is not a silent concession to candidate output.

A second agent using the same incorrect specification can still agree on the wrong answer. The external anchors are the real request, application contract, reference behavior, accepted quality examples, and relevant real-world feedback. No collection of AI votes establishes user benefit or universal correctness.

### Observe the actual candidate

Use existing runtime controls and native tools to run the candidate without unrelated secrets or privileged effects. Protect the evaluator, check discovery, acceptance inputs, and authoritative outputs from candidate mutation. A directory name, prompt prohibition, file hash, or candidate-generated receipt is not proof of isolation or honest execution.

Demonstrate claimed boundaries with harmless owned checks. A protected local process does not imply that browser sessions, connected tools, CI, or deployment permissions are equally contained. Unsupported protection remains an explicit limitation. Do not invoke a privileged verifier on arbitrary candidate-controlled code as a shortcut.

Evidence should identify the requirement version, actual source tree or build, relevant dependencies, environment and run, data/auth mode, tool/check version, expected and observed results, and review scope. Reuse native receipts. A commit alone is insufficient if the working tree or running build differs.

A code change invalidates affected evidence. A new candidate cannot inherit old screenshots merely because the route name is unchanged. Refresh relevant checks and reviewer coverage, retain failure evidence, and clean up only owned resources. Content digests establish identity, not correctness.

### Make the judgment finite and challengeable

The reviewer starts with the requirement, artifact, and direct observations before the author's justification. It can run additional authorized checks. Findings identify the concrete issue, affected requirement or quality criterion, evidence, and condition for resolution. Distinguish blockers from optional refinements. Challenge false rejections as well as false approvals.

For required checks, missing, failed, stale, or unavailable is not accepted. A genuinely inapplicable check may be excluded with a reason. A required-but-unavailable check cannot be relabeled inapplicable. Keep existing native status contracts rather than inventing another vocabulary.

**Final rule:** every applicable required outcome is established, required independent review covers the final candidate, evidence is current, and only authorized delivery effects occur. Local acceptance, PR readiness, deployed behavior, and observed reliability over time are separate claims. Tiny tasks may use the existing short path but must not claim independent review that did not happen.

### Verify the verifier

Use a known-valid candidate, a meaningful behavioral defect, and missing or stale evidence. Confirm acceptance and rejection for the intended reasons. A syntax error does not show that a persistence or authorization defect would be detected. A verifier that rejects everything is also broken.

Finite checks establish scoped confidence, not the absence of all bugs. The user's target is routine AI-operated engineering and assessment. Occasional calibration of the quality standard is different from requiring the user to inspect every implementation. An expert-equivalence claim requires a credible independent reference for that task class, not self-assigned labels.

## 8. Improvement without overfitting

Skills changes inference-time guidance, examples, tools, and evaluation. It does not inherently train model weights. “Overfitting” here means tuning that complete system to known tasks or a narrow judge at the expense of unseen work, valid alternatives, or creative capability.

### Two decisions, never one

**Artifact acceptance:** is this result good enough? **Intervention adoption:** did this change to Skills or tooling improve the system? A better method can still produce an unacceptable artifact. An acceptable artifact does not establish that a new instruction helped.

A candidate improvement needs a demonstrated failure, a causal hypothesis, the owning layer, a small proposed intervention, and a predeclared comparison and resource budget. Use the existing task or change record. Do not create a separate experimentation service.

### What happens when it does not help

Inspect the earliest consequential wrong decision and the actual outcome. Distinguish an unclear standard, missing context, poor design choice, confusing tool, unavailable environment, wrong evaluator, and model limitation. Do not reflexively add prose.

| Finding | Preferred response |
| --- | --- |
| The desired quality was never defined | Establish the relevant expectation without inventing unrelated requirements |
| Canonical behavior was not discovered | Improve targeted access or an application exemplar |
| The operation is repeatedly misexecuted | Repair the native tool or narrow adapter |
| The chosen direction is poor | Reconsider the design rather than accumulate cosmetic fixes |
| A good artifact is rejected or a bad one accepted | Repair and recalibrate the evaluator |
| The intervention shows no reliable benefit | Retain the accepted baseline or simplify. Report uncertainty |
| The current method cannot reach the bar | Try a materially different supported approach within authority and budget |

Preserve useful work, the strongest candidate, and failed evidence. Retry only when there is a new observation, changed hypothesis, or justified correction. Diagnose supported recovery before declaring a real blocker. When the finite budget or permission boundary is reached, leave the result unaccepted rather than manufacturing completion.

### Use greediness as a local decision rule, not a universal optimizer

Within a task, choose the next authorized action that most usefully resolves the uncertainty preventing a defensible result. Across tasks, prefer the smallest intervention that removes an important recurring limitation with plausible transfer and manageable maintenance cost.

Mandatory safety and acceptance constraints come first. A frequent cosmetic problem must not crowd out a serious data-integrity risk. Allow bounded exploration and dependent improvements where local refinement has stalled. A better browser interface may be valuable because it enables evaluation, even before the final quality metric improves.

### Test transfer and retained flexibility

Compare accepted baseline, candidate, and where useful a simpler guidance variant under the same task inputs, model/settings, tools, environment, authority, and budget. A model or runtime change is a separate intervention. Preserve the same required boundaries in any simpler control.

Include the original failure, an unseen task from that family, ordinary regression work, and a counterexample where the new default should not apply. For a broad claim, test another context or repository. Include a different valid solution to ensure the judge does not mistake reference similarity for quality.

For creative work, evaluate different successful directions and ambiguous cases. Permit “neither acceptable” and “insufficient evidence.” Keep functionality and required engineering quality binding, but do not reward novelty for its own sake. Faithful imitation is required only when the brief requests it.

Separate development cases from held-out cases by meaningful tasks or contexts, not just renamed variables or recolored screens. Record exposure and refresh cases when they become tuning material. New real work is part of the evidence for transfer.

Use paired attempts and repetition only to the extent justified by risk and variation. Retain failed launches, interruptions, and unavailable results. Do not retry one arm until it wins. Diagnose shared environment failures before attributing differences to the model or instructions.

**Adoption:** promote only with evidence of useful gain or justified lower overhead, no observed material regression in required capabilities, and an explicit authorized decision. Simplification and deletion are valid outcomes. Automatic rule promotion stays paused. Reassess guidance when tools or models change.

Anthropic's evaluation guidance distinguishes observed outcomes from agent narratives and recommends assessing valid results without unnecessarily prescribing the route. Its emphasis on balanced cases informs the counterexample checks here. These are evaluation design choices, not a guarantee of generalization. [E4]

## 9. Repository shape and compatibility

The logical core is small. That does not require renaming everything into exactly three folders. Start by assigning responsibilities to current owners and remove duplication through reviewable changes. Keep any existing interface or resource whose usefulness is established.

```text
Skills/
  README.md                     Mission, operating boundaries, demonstrated scope
  catalog.yaml                  Existing discovery and provenance
  global-instructions/AGENTS.md User policy, not a second engineering handbook
  skills/
    follow-instructions/        Engineer entry and proportionate task method
    verify-work/                Acceptance and independent evidence methods
    skill-creator/              Controlled improvement and adoption procedure
    <existing domain owners>/   Focused expertise where it changes a decision
      references/               Worked examples and decision guidance, as needed
      assets/                   Relevant licensed/sanitized visual material
      scripts/                  Only justified reusable operations
  scripts/                      Existing install and structural checks
  evals/                        Existing diagnostics, focused cases, result records
```

This is an ownership map, not an instruction to create empty directories or every possible resource. `engineer / verify / improve` are the conceptual responsibilities. Consolidated installed names may be proposed later if they reduce real routing or maintenance cost. Preserve selected installation, dependency resolution, provenance, and policy precedence during any migration.

The inspected README already separates app-owned truth, application CLIs, and evaluator diagnostics. It documents Linktree integration but does not establish the installed runtime's readiness. Preserve that separation. [R1]

### Smallest implementation sequence

First, establish the installed baseline and select one real task. Second, fix the specific tool, context, or acceptance gap that prevents its complete delivery. Third, add only the worked examples and quality methods needed for that task. Fourth, compare the complete candidate and retain the useful changes. Update the mission and map as part of the approved repository work, not as an unrequested side effect.

Use current functions and scripts where possible. A broad evaluation rewrite is not a prerequisite. Do not require a new container build for each instruction change. Inspect CI side effects before an authorized push. Retain previous installed packages and tool versions for a supported rollback rather than changing global installations silently.

**Ownership rule:** shared engineering methods stay in Skills, application policies and examples stay with the application, repeatable operations stay with their tool, and permissions stay with the runtime. There should be one authoritative owner for each changing fact.

## 10. Build sequence, milestones, and the finish line

### First complete experiment

Use Linktree first because its CLI binding is documented, not because this document has verified its environment. The documented runtime includes real local Shrunk, so confirm the dependency, both source identities, supported authentication, isolated data, and browser access before treating the journey as available. A development-login run does not establish real CAS behavior. [R1] [R3]

Select an actual requested change with a meaningful UI or integration concern. Do not invent a defect. Freeze the current baseline and agreed candidate scope. Establish required acceptance, the independent review mechanism, and the permitted local/publication effects. Resolve these through bounded discovery before dependent implementation.

Prove the full scoped change using real behavior, inspected rendering where relevant, a meaningful negative control, fresh review, necessary repairs, and affected rechecks. A fresh context must repeat the supported verification without hidden manual preparation. Complete the requested delivery only when its evidence and permissions exist.

This is not a mock-only pilot. It is one complete real outcome with a deliberately limited scope.

### Expand responsibility, not the agent roster

| Milestone | Evidence needed to advance | What it does not establish |
| --- | --- | --- |
| **M1. One trustworthy delivery** | Real result, meaningful verifier controls, current evidence, correct boundaries, fresh-context repeatability | General task competence or a better Skills version |
| **M2. A transferable task family** | A matched baseline comparison, unseen related tasks, ordinary regression work, valid alternatives, and justified cost | Competence in every discipline |
| **M3. A repository maintainer** | Several actual task types, one substantial feature, interrupted-work continuation, and a credible follow-up change | Cross-repository transfer or production authority |
| **M4. A dependable maintainer for two repositories** | Reuse of the same method with local contracts, sustained real work, acceptable quality, and no routine human engineering rescue | Universal expert equivalence |
| **M5. Authorized service ownership** | Supported operational diagnosis and recovery, preserved important state, relevant runtime observations over time | Permission for unrelated or irreversible production actions |

Breadth, difficulty, and authority advance separately. A strong diagnosis can remain read-only. A staging recovery exercise does not grant deployment permission. Adding parallel agents requires a demonstrated bottleneck, independent work ownership, and integrated verification.

### Measurements that inform the decision

For a declared workload, report **independently accepted task-runs without corrective human engineering divided by all selected task-runs**. A task-run includes its agreed finite repair budget. Report individual task coverage, repetitions, retries, blocked cases, and results by task family rather than allowing easy tasks to hide difficult failures.

Keep planned approvals separate from the user diagnosing bugs, redesigning screens, or repairing code. Record escaped defects, false approvals, false rejections, relevant quality judgments, setup/review/repair effort, and total cost per accepted result. Do not equate tokens or elapsed time with money when the actual conversion is unknown.

Choose workload composition, acceptable intervention burden, critical failure policy, cost limits, and an observation window before assessing adoption. Do not treat “30 tasks,” “90%,” or “four weeks” as universal reliability thresholds. Those earlier illustrative numbers do not become contractual gates in v2. Small samples justify narrow conclusions. Preserve unacceptable outputs as unaccepted rather than averaging their defects away.

**Practical finish line:** meaningful work can be delegated across two real repositories, delivered at the agreed quality bar, and maintained through subsequent changes without routine corrective engineering from Soham. Claims remain limited to demonstrated work and environments.

After that, spend the main effort on the applications. Improve Skills only when real work exposes a reason. The goal is to reduce the engineering responsibility the user carries, not create an indefinitely expanding framework project.

## 11. Worked scenario: one feature, several disciplines

**Illustrative request, not a current Linktree defect:** “Improve the profile editor's visual quality. Preserve the existing behavior and permissions, make saving and cancellation clear, and deliver a reviewed PR.”

The engineer inspects the current editor, relevant callers, design references, authoritative validation and permission owners, and supported runtime. The task record distinguishes appearance, usability, persistence, cancellation, and denied operations. Requirements come from the actual request and contracts. This scenario does not prescribe endpoints, components, or a storage design that have not been inspected.

Tools prepare an isolated instance and capture representative content and states. The agent uses relevant accepted and rejected visual examples, plus the application's own well-integrated feature, instead of loading every domain reference. It diagnoses whether the gap is composition, implementation fidelity, or evaluator judgment. A material design direction follows the existing approval policy.

The agent implements a representative slice using the real components and canonical owners. It has freedom to choose a composition different from the references. It does not have freedom to remove required behavior, create competing permission logic, or claim a picture is an implemented interface.

Protected checks exercise the independently expected persistence, cancellation, and authorization effects. A fresh reviewer assesses the actual render and interaction against the agreed bar, then inspects integration and maintainability. Where justified, a disposable follow-up reveals whether a normal extension creates duplicated rules or unexpected coupling.

Suppose the result is functionally correct but visually mediocre. It remains below acceptance. Determine whether the judge approves the wrong examples, the renderer fails to match the selected direction, or the direction itself is weak. Repair the responsible capability. Preserve the best candidate rather than rewarding the latest iteration.

Once all required gates cover the final artifact, perform only the approved publication steps and inspect required current-head CI. Do not merge. Local browser evidence does not establish deployed behavior.

Finally, decide whether a reusable lesson exists. It may become a concise visual case, an application check, a clearer tool response, or nothing permanent. Test any proposed shared change on a different layout or task before claiming improvement. The actual feature can be accepted even if the Skills intervention shows no measurable benefit.

## 12. Decision rationale and revisit conditions

These are explicit engineering judgments, not proven performance claims.

| Decision | Reason and trade-off | Revisit when |
| --- | --- | --- |
| One integration owner, separate substantive review | Keeps accountability and reduces conflicting handoffs. May limit throughput | Independent work is demonstrably blocked by sequential execution and parallel integration can be verified |
| Requirements separate from defaults and examples | Preserves alternative solutions while keeping real constraints binding. Requires clear classification | A default repeatedly conceals a genuine requirement or a rule proves unnecessarily restrictive |
| Automate stable mechanics with native tools first | Removes repeated execution errors without replacing judgment. Tool maintenance is a real cost | An existing tool is more confusing or restrictive than a smaller supported operation |
| Annotated, diverse examples | Makes judgment inspectable and task-specific. Risks anchoring and stale guidance | Transfer tests or new work reveal imitation, contradiction, or no benefit |
| Upstream design checkpoints for consequential decisions | Avoids polishing a poor foundation. Adds some early effort | The checkpoint repeats known decisions or demonstrably adds no useful signal |
| Protected checks plus calibrated judgment | Combines mechanically testable properties with less formal quality assessment. Neither is complete | False acceptance, false rejection, or a new runtime invalidates the assumptions |
| Targeted change probes for maintainability | Tests a realistic consequence rather than a slogan. Cannot prove years of evolution | The probe is speculative, expensive, or no longer representative |
| Controlled improvements with removal as an option | Limits overfitting and rule accumulation. Requires comparison effort | The evaluation itself becomes a larger burden than the failure it addresses |
| Logical redesign, incremental replacement | Avoids preserving needless prose without discarding working integration | A coherent interface change has clear benefit, compatibility evidence, and approval |

### Open implementation facts, not open architectural commitments

The selected application task, installed Skills and CLI versions, supported reviewer, protected execution path, available render tooling, initial product references, and exact run budget must be established before implementation. A source document is not evidence that those capabilities work.

The main uncertainty is whether this combination of guidance, tools, examples, and calibrated assessment improves the user's actual workload. That is the first experiment's purpose. No small benchmark or agreement between AI agents establishes decades of expertise across all domains.

**Final design test:** does each added instruction, example, check, or tool either enforce a necessary boundary or make useful engineering work more reliable, better, or less burdensome without narrowing valid solutions? If not, it should not become part of the permanent system.

## Sources and evidence boundaries

The architecture and acceptance requirements above are proposed design decisions. The sources provide current repository context and selected supporting observations, not validation of the proposed system. External sources were checked on October 13, 2026. No application task, runtime containment test, model comparison, independent peer review, installation, remote CI, or deployment was performed for this document. Document rendering and packaging checks are separate from those engineering claims.

<span id="source-v1"></span>**V1. Original design:** `skills-verified-autonomous-engineering.md`, version 1.0, October 13, 2026. Read in full and preserved unchanged. Its compatibility-first mission and evidence model are the baseline for this revision.

| Reference | Source | Limited use in this design |
| --- | --- | --- |
| [R0] | Skills `main` commit | Reconfirmed source baseline, not installed/runtime identity |
| [R1] | Skills README at that commit | Current ownership, installation, CLI binding, and documented evaluation limits |
| [R2] | Skills collaboration contract at that commit | Current authority, approval, no-merge, and paused rule-promotion policies |
| [R3] | Original document's inspected CLI findings | Linktree/Shrunk and authentication distinctions. Not a new live CLI inspection |
| [E1] | Anthropic, *Effective context engineering for AI agents* | Selective context and diverse examples rather than brittle prompt rules |
| [E2] | Anthropic, *Writing effective tools for AI agents* | Clear tool contracts, useful outputs, and agent-use evaluation |
| [E3] | Agent Skills, *Specification* | Existing packaging and selectively loaded supporting resources |
| [E4] | Anthropic, *Demystifying evals for AI agents* | Outcomes versus narratives, balanced cases, and flexible assessment |
| [E5] | Anthropic, *Harness design for long-running application development* | Evaluator calibration, design plateaus, and risks of over-iteration |
| [E6] | Google, *What to look for in a code review* | Integration, present needs, understandable complexity, useful tests |
| [E7] | W3C WAI, *Evaluating Web Accessibility Overview* | Limits of automated accessibility assessment |
| [E8] | OpenAI, *Harness engineering* | Supporting precedent for agent-readable environments and mechanically enforced constraints, not evidence of this system's performance |

[R0]: https://github.com/Astatide1337/Skills/commit/52ef9c11fc6ac42e01bd6aed78ae15bf46250290
[R1]: https://github.com/Astatide1337/Skills/blob/52ef9c11fc6ac42e01bd6aed78ae15bf46250290/README.md
[R2]: https://github.com/Astatide1337/Skills/blob/52ef9c11fc6ac42e01bd6aed78ae15bf46250290/global-instructions/AGENTS.md
[R3]: #source-v1
[V1]: #source-v1
[E1]: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
[E2]: https://www.anthropic.com/engineering/writing-tools-for-agents
[E3]: https://agentskills.io/specification
[E4]: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
[E5]: https://www.anthropic.com/engineering/harness-design-long-running-apps
[E6]: https://google.github.io/eng-practices/review/reviewer/looking-for.html
[E7]: https://www.w3.org/WAI/test-evaluate/
[E8]: https://openai.com/index/harness-engineering/
