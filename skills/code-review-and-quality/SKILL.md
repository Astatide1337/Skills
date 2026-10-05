---
name: code-review-and-quality
description: Review a code change for correctness, design, security, and performance before merge.
---

# Code Review and Quality

## Overview

Review the original request, final diff, affected callers, tests, and current evidence. Scale the depth to the changed behavior and risk. Finish with concrete findings, checks inspected, unresolved limits, and readiness at the reviewed revision.

**The approval standard:** Approve a change when it definitely improves overall code health, even if it isn't perfect. Perfect code doesn't exist — the goal is continuous improvement. Don't block a change because it isn't exactly how you would have written it. If it improves the codebase and follows the project's conventions, approve it.

## Evidence and workspace boundary

Inspect only the supplied project root and artifacts explicitly named by the
task. Do not search parent directories, `/tmp`, evaluator/grader paths, or
unrelated repositories for a missing source tree, diff, manifest, or result.
If required evidence is absent, say exactly what is missing and provide a
bounded review plan; do not invent findings or claim a review was completed.

When the task is text-only, offline, or says not to browse/install/run
commands, use only the supplied source and release notes. Do not run package
audits, fetch changelogs, query registries, or install dependencies. Mark
external maintenance, vulnerability, and license facts as unknown until
authorized evidence is supplied.

`Review-only`, `do not edit`, and `do not run the application` still permit
read-only inspection of supplied files and diffs. Open those artifacts before
reporting a finding. Ask for missing evidence only after checking the declared
workspace; do not replace an available patch with a hypothetical review plan.

## When to Use

- Before merging any PR or change
- After completing a feature implementation
- When another agent or model produced code you need to evaluate
- When refactoring existing code
- After any bug fix (review both the fix and the regression test)

## The Five-Axis Review

Every review evaluates code across these dimensions:

### 1. Correctness

Does the code do what it claims to do?

- Does it match the spec or task requirements?
- Are edge cases handled (null, empty, boundary values)?
- Are error paths handled (not just the happy path)?
- Does it pass all tests? Are the tests actually testing the right things?
- Are there off-by-one errors, race conditions, or state inconsistencies?

### 2. Readability & Simplicity

Can another engineer (or agent) understand this code without the author explaining it?

- Are names descriptive and consistent with project conventions? (No `temp`, `data`, `result` without context)
- Is the control flow straightforward (avoid nested ternaries, deep callbacks)?
- Is the code organized logically (related code grouped, clear module boundaries)?
- Are there any "clever" tricks that should be simplified?
- **Could this be done in fewer lines?** (1000 lines where 100 suffice is a failure)
- **Are abstractions earning their complexity?** (Generalize for demonstrated callers and contracts; do not invent future consumers.)
- Would comments help clarify non-obvious intent? (But don't comment obvious code.)
- Are there dead code artifacts: no-op variables (`_unused`), backwards-compat shims, or `// removed` comments?
- **Is a new conditional bolted onto an unrelated flow?** That's a design smell, not a nit — push the logic into its own helper, state, or policy instead of tangling an existing path.
- **Do repeated conditionals on the same shape appear?** They signal a missing model or dispatcher. A "temporary" branch is usually permanent debt.

### 3. Architecture

Does the change fit the system's design?

- Does it follow existing patterns or introduce a new one? If new, is it justified?
- Does it maintain clean module boundaries?
- Is there code duplication that should be shared?
- Are dependencies flowing in the right direction (no circular dependencies)?
- Is the abstraction level appropriate (not over-engineered, not too coupled)?
- **Does this refactor reduce complexity or just relocate it?** Count the concepts a reader must hold to follow the change. If a "cleaner" version leaves that count unchanged, it isn't cleaner — prefer the restructuring that makes whole branches, modes, or layers disappear over one that re-centralizes the same logic. Prefer deleting an abstraction to polishing it.
- **Is feature-specific logic leaking into a shared or general-purpose module?** Keep logic in its owning layer, reuse the existing canonical helper instead of a near-duplicate, and don't normalize architectural drift.
- **Are type boundaries explicit?** Question gratuitous `any`/`unknown`/optional/casts and silent fallbacks that paper over an unclear invariant — making the boundary explicit often makes the surrounding control flow simpler.

### 4. Security

Does the change introduce vulnerabilities? Use this section as a bounded screen.
Invoke `security-and-hardening` for a deeper audit when a change adds or modifies
authentication, authorization, tenant/object scope, secrets or sensitive data,
unsafe execution/rendering/fetch boundaries, externally reachable integrations,
dependency/build trust, deployment privilege, or another material trust boundary;
also invoke it when this screen finds a plausible exploitable path.

For a plausible trust-boundary flaw, the finding is incomplete unless it states
the attacker-controlled input, missing enforcement boundary, reachable asset or
victim, impact, narrow remediation, and a negative test using two distinct
ordinary identities where authorization scope is involved. Explicitly hand the
case to `security-and-hardening` for deeper analysis; do not merely mention that
security deserves attention.

- Is user input validated and sanitized?
- Are secrets kept out of code, logs, and version control?
- Is authentication/authorization checked where needed?
- Are SQL queries parameterized (no string concatenation)?
- Are outputs encoded to prevent XSS?
- Are dependencies from trusted sources with no known vulnerabilities?
- Is data from external sources (APIs, logs, user content, config files) treated as untrusted?
- Are external data flows validated at system boundaries before use in logic or rendering?

### 5. Performance

For a suspected regression, use the measured workflow in `references/backend-performance.md`. Does the change introduce performance problems?

- Any N+1 query patterns?
- Any unbounded loops or unconstrained data fetching?
- Any synchronous operations that should be async?
- Any unnecessary re-renders in UI components?
- Any missing pagination on list endpoints?
- Any large objects created in hot paths?

## Handling review feedback

Before implementing a review comment, restate the requested change, locate the relevant code, and verify that the premise is technically correct for this repository. Ask when scope is ambiguous. Push back with evidence when a suggestion would break behavior, violate an established constraint, or add unjustified complexity. Never perform agreement; either implement the verified request or explain the concrete conflict. See `references/review-feedback.md`.

## Behavior-preserving simplification

When the goal is cleanup, first lock down observable behavior and then reduce concepts, branches, indirection, and duplication. Do not mix semantic changes into a simplification pass. See `references/behavior-preserving-simplification.md`.

## Structural Remedies

When you flag a structural problem, propose the move — not just the problem. A review that only says "this is complex" leaves the author guessing. Reach for a named restructuring:

- **Replace a chain of conditionals** with a typed model or an explicit dispatcher.
- **Collapse duplicate branches** into a single clearer flow.
- **Separate orchestration from business logic** so each reads on its own.
- **Move feature-specific logic** out of a shared module into the package that owns the concept.
- **Reuse the canonical helper** instead of a bespoke near-duplicate.
- **Make a type boundary explicit** so downstream branching disappears.
- **Delete a pass-through wrapper** that adds indirection without clarifying the API.
- **Extract a helper, or split a large file** into focused modules.

Prefer the remedy that removes moving pieces over one that spreads the same complexity around.

## Change Sizing

Keep one review unit coherent and small enough to inspect its behavior,
callers, and tests together. Split independent changes when that improves
review or rollback. Diff size and file size are inspection signals, not hard
caps or reasons to extract helpers without a clearer responsibility.

## Change Descriptions

Every change needs a description that stands alone in version control history.

**First line:** Short, imperative, standalone. "Delete the FizzBuzz RPC" not "Deleting the FizzBuzz RPC." Must be informative enough that someone searching history can understand the change without reading the diff.

**Body:** What is changing and why. Include context, decisions, and reasoning not visible in the code itself. Link to bug numbers, benchmark results, or design docs where relevant. Acknowledge approach shortcomings when they exist.

**Anti-patterns:** "Fix bug," "Fix build," "Add patch," "Moving code from A to B," "Phase 1," "Add convenience functions."

## Review Process

### Step 1: Understand the Context

Before looking at code, understand the intent:

```
- What is this change trying to accomplish?
- What spec or task does it implement?
- What is the expected behavior change?
```

### Step 2: Review the Tests First

Tests reveal intent and coverage:

```
- Do tests exist for the change?
- Do they test behavior (not implementation details)?
- Are edge cases covered?
- Do tests have descriptive names?
- Would the tests catch a regression if the code changed?
```

### Step 3: Review the Implementation

Walk through the code with the five axes in mind:

```
For each file changed:
1. Correctness: Does this code do what the test says it should?
2. Readability: Can I understand this without help?
3. Architecture: Does this fit the system?
4. Security: Any vulnerabilities?
5. Performance: Any bottlenecks?
```

### Step 4: Categorize Findings

Label every comment with its severity so the author knows what's required vs optional:

| Prefix | Meaning | Author Action |
|--------|---------|---------------|
| *(no prefix)* | Required change | Must address before merge |
| **Critical:** | Blocks merge | Security vulnerability, data loss, broken functionality |
| **Nit:** | Minor, optional | Author may ignore — formatting, style preferences |
| **Optional:** / **Consider:** | Suggestion | Worth considering but not required |
| **FYI** | Informational only | No action needed — context for future reference |

This prevents authors from treating all feedback as mandatory and wasting time on optional suggestions.

**Lead with what matters.** Order findings by leverage: correctness and security first, then structural regressions and missed simplifications, then everything else. Don't bury a real issue under cosmetic nits — a few high-conviction comments beat a long list. If you have one structural problem and ten nits, the structural problem *is* the review.

### Step 5: Verify the Verification

Check the author's verification story:

```
- What tests were run?
- Did the build pass?
- Was the change tested manually?
- Are there screenshots for UI changes?
- Is there a before/after comparison?
- Are expectations independent of candidate output, and do they exercise the final tree or running revision?
- Did any changed test, feature map, discovery rule, scorer, lint/import boundary, or CI configuration remove coverage? Require an explicit reason and a violating fixture before accepting a structural replacement.
```

## Independent Review

For substantive implementation, an independent reviewer must inspect the
current diff and its evidence before the integrating owner claims substantive
work complete or recommends merge. A draft may remain open while this review
is pending. The reviewer may be a person or an agent other than the integrating
author; choosing a different model is optional. The integrating owner remains
accountable for resolving findings and verifying the final head. The author's
own reread, green tests, and a model's summary of the author's account do not
satisfy the independent gate. If a reviewer is unavailable, leave the gate
pending and say so.
Retain an inspectable review result that identifies the separate reviewer,
the exact diff or artifact reviewed, evidence inspected, and findings. An
empty wait, requested review without a returned result, or the author's
statement that review happened is not that result. Confirm the reviewed
artifact still matches the final artifact before claiming the gate passed.

## Dead Code Hygiene

After any refactoring or implementation change, check for orphaned code:

1. Identify code that is now unreachable or unused
2. Verify its callers and ownership.
3. Remove it when the requested change made it obsolete and removal is within
   scope; ask only if a live consumer or ownership decision remains unclear.

Don't leave dead code lying around — it confuses future readers and agents. But don't silently delete things you're not sure about. When in doubt, ask.

## Handling Disagreements

When resolving review disputes, apply this hierarchy:

1. **Technical facts and data** override opinions and preferences
2. **Style guides** are the absolute authority on style matters
3. **Software design** must be evaluated on engineering principles, not personal preference
4. **Codebase consistency** is acceptable if it doesn't degrade overall health

Resolve material in-scope defects before readiness. Keep unrelated cleanup separate; filing or assigning an issue requires the corresponding authority.

## Honesty in Review

When reviewing code — whether written by you, another agent, or a human:

- **Don't rubber-stamp.** "LGTM" without evidence of review helps no one.
- **Don't soften real issues.** "This might be a minor concern" when it's a bug that will hit production is dishonest.
- **Quantify problems when possible.** "This N+1 query will add ~50ms per item in the list" is better than "this could be slow."
- **Push back on approaches with clear problems.** Sycophancy is a failure mode in reviews. If the implementation has issues, say so directly and propose alternatives.
- **Accept override gracefully for technical judgment.** If the author has full context and disagrees about a design trade-off, defer to their judgment. An override does not waive required verification or independent review. Comment on code, not people — reframe personal critiques to focus on the code itself.

## Dependency Discipline

Part of code review is dependency review:

**Before adding any dependency:**
1. Does the existing stack solve this? (Often it does.)
2. How large is the dependency? (Check bundle impact.)
3. Is it actively maintained? (Check last commit, open issues.)
4. Does it have known vulnerabilities? (`npm audit`)
5. What's the license? (Must be compatible with the project.)

**Rule:** Prefer standard library and existing utilities over new dependencies. Every dependency is a liability.

**Upgrading an existing dependency** is a code change like any other, and the riskiest upgrades are the ones merged in bulk with a message like "bump deps." Review them with the same discipline:

1. **Read the changelog, not just the version number.** Semver is a promise the maintainer may not have kept — a "patch" can carry a behavioral change. For a major bump, read the migration notes and find what breaks.
2. **One dependency per change.** Upgrade and merge them individually (or in small related groups). When a bulk bump breaks the build, you've lost which package did it; a single-package change makes the cause obvious and the revert clean.
3. **Let the tests decide.** The upgrade is verified by a green suite before *and* after, not by "it installed." If coverage around the dependency's behavior is thin, that gap is the real finding — add a test first.
4. **Mind the transitive graph.** Most installed packages are ones nobody chose directly. Review the lockfile diff, not just `package.json`; a single direct bump can pull in dozens of indirect changes.
5. **Keep the lockfile honest.** Commit it, review its diff, and never hand-edit it. The lockfile is the thing that actually pins what ships.

For triaging `npm audit` findings and supply-chain risk (typosquatting, compromised maintainers), follow the `security-and-hardening` skill — this section covers the upgrade *workflow*, that one covers the security verdict.

## Completion

Resolve material findings, inspect the final diff and affected checks, and
confirm the independent review still covers the final artifact. Keep
failed, unavailable, and unrun checks visible; a review recommendation does
not authorize merge or deployment.

Read `references/security-checklist.md` or `references/performance-checklist.md`
only when the changed surface needs that deeper review.

## Execution boundary

Apply the shared [execution boundary](../follow-instructions/references/principles/authority-and-claims.md#execution-boundary).
Keep the task-specific restrictions above; this skill grants no additional effects.
