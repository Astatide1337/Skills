# Skills catalog evaluation and hardening report

Date: 2026-08-18
Status: implementation complete; acceptance evidence remains intentionally
inconclusive where the experiment is underpowered or the grader is defective.

## Executive result

The evaluation program now covers the full 24-skill catalog: 23 ordinary
skills plus `skill-creator`. The catalog contains 107 contracts: 83 tuning
cases and 24 held-out cases. Every catalog case has an explicit execution mode,
bounded tools, deterministic graders, and a qualitative rubric.

The campaign produced 1,290 retained provider attempts and 132 additional
attempts quarantined from analysis after a runtime-alias race. All retained
provider calls used `gpt-5.6-luna` with maximum reasoning effort. The results
are useful for finding instruction and measurement defects, but they do not
support a claim that the revised skills are universally or deterministically
better yet.

The most important conclusion is methodological: more repeated runs cannot
repair a missing fixture, a grader that rewards arbitrary vocabulary, or a
holdout that has been exposed to tuning. The next quality gains should come
from better contracts, calibrated graders, and blinded qualitative review
before increasing the run count further.

## What was implemented

### Contract-driven evaluation

- Converted the catalog to a normalized contract layer while preserving the
  existing per-skill manifests as tuning input.
- Added 48 additional fixture-free tuning cases and 24 frozen held-out cases.
- Required explicit `text_only` or `workspace_write` execution modes.
- Rejected web search, MCP, browser, Firecrawl, and broad network use in the
  offline evaluation path.
- Added reference calibration and leave-one-grader-out calibration. The
  catalog calibration passes all 107 cases.
- Added immutable skill and contract digests. Regrading now refuses to score a
  materialized contract if its digest does not match the run metadata.
- Added paired, randomized baseline/treatment arms, case-clustered bootstrap
  intervals, invalid-run accounting, critical safety gates, and incomplete
  coverage detection.
- Added a runtime-alias integrity check. A skill cannot be treated as a
  comparable baseline or treatment if the runtime name was changed.
- Fixed the network classifier so local `rg --files`, `find`, and similar
  manifest inspection are not mistaken for network access, while actual
  `curl`, package-manager, Git, and network-error behavior remains fail-closed.
- Added blinded review packet generation. The clean current `skill-creator`
  v7 packets were reviewed by three disjoint independent Luna subagents: the
  panel found 1 treatment win, 1 baseline win, and 4 ties. This is an
  independent-model panel, not human adjudication; no human review summary
  has been completed.

The follow-up hardening cycle now also:

- Preserves the original `evals/catalog/heldout.json` as v1 evidence and makes
  `evals/catalog/heldout-v2.json` the active catalog holdout.
- Removes the duplicate `execution` key from the active shadcn case and tests
  loading-state semantics with accepted alternatives such as `isDeleting` and
  `deleting`.
- Replaces the skill-creator holdout's incidental `expectation` requirement
  with outcome-oriented deterministic checks.
- Accepts equivalent evidence vocabulary for consumer mapping, verification,
  debugging, source-boundary, React scope, and accessibility cases while
  retaining separate gates for the underlying concepts.
- Makes review packet IDs opaque, removes the case identifier from public task
  packets, redacts temporary provider paths, requires both arms to have valid
  grades, and emits a reviewer protocol.
- Rejects duplicate JSON keys in active contract documents and tests that the
  active catalog cannot accidentally load the archived holdout.

This follows the same separation used by OpenAI's evaluation guidance:
deterministic graders should test explicit task outcomes, while qualitative
review is needed for dimensions that cannot be reduced safely to a string
match. See the [OpenAI graders reference](https://developers.openai.com/api/reference/resources/graders)
and the [OpenAI Evals build guide](https://github.com/openai/evals/blob/main/docs/build-eval.md).

### Skill hardening

The current working tree includes focused revisions to the skills, including:

- API/interface design: server-verified caller identity is separated from
  caller-supplied identifiers, tenant fields, and roles.
- Production safety: consumer mapping now includes workloads, service
  accounts, controllers, scheduled jobs, secrets/backups, dashboards, and
  runbooks; text-only/offline tasks cannot perform live probes.
- Cloudflare deployment: fail-closed authentication, target and promotion
  gates, bounded command classification, rollback evidence, and post-deploy
  verification.
- UI quality: no invented routes, links, endpoints, or domain objects when
  the supplied evidence does not define them.
- Composition and React guidance: React-version uncertainty is explicit, and
  `useContext` versus React 19 `use()` is decided by evidence and resource
  semantics rather than a blanket migration rule.
- Verification: every completion claim records what is proven, what remains
  unknown, and what is only a claim.
- Shadcn and component guidance: safer registry/version handling, explicit
  artifact boundaries, accessibility state requirements, and self-audit.
- Debugging, diagnosing, minimalism, performance, prototype, security,
  receiving review, and web guidance: stronger evidence boundaries,
  fail-closed behavior, measurable acceptance criteria, and offline research
  rules where appropriate.
- `skill-creator`: a v2 contract workflow now covers design, tuning, frozen
  holdouts, grader calibration, reference artifacts, integrity checks, and
  review. It explicitly tells future skill authors to grade outcomes and
  semantic alternatives rather than force incidental vocabulary.

## Evaluation campaigns

Each paired trial means one baseline run and one treatment run. The interval is
clustered by independent skill/case, not by repeated model attempt, so three
trials do not pretend to be three independent tasks.

| Campaign | Scope | Attempts | Valid / invalid | Paired trials | Automated result |
|---|---:|---:|---:|---:|---|
| Broad old-vs-current tuning sweep | 23 skills, 75 independent cases | 480 | 441 / 39 | 204 | +2.67 percentage points; 95% CI −2.67 to +8.44; inconclusive |
| Broad old-vs-current held-out pass | 23 skills, 21 exposed cases | 138 | 132 / 6 | 63 | +6.35 points; 95% CI −6.35 to +19.05; diagnostic only |
| Clean iteration-2 tuning | 5 revised skills, 19 cases | 114 | 114 / 0 | 57 | +3.51 points; 95% CI −3.51 to +12.28; inconclusive |
| Post-tuning regression guard | Same 5 skills, 5 held-out cases | 30 | 30 / 0 | 15 | +13.33 points; 95% CI −13.33 to +40.00; inconclusive |
| `skill-creator` tuning | 3 cases | 18 | 17 / 1 | 8 comparable pairs | 100% vs 100% among valid paired runs; no lift shown |
| `skill-creator` regression guard | 1 exposed held-out case | 6 | 6 / 0 | 3 | 0% vs 0% because the frozen grader requires arbitrary vocabulary; invalid for quality decisions |

The retained runs have no critical safety failures in the valid paired arms.
That is a useful safety signal, not evidence of perfect task quality.

The 132 quarantined attempts came from one incorrectly scoped alias run in
which the alias was applied globally instead of only to `skill-creator`. They
remain recoverable under:

```text
/home/sohamb/.local/share/skills-evals-invalid-20260827/iteration-2-alias-race/
```

They are excluded rather than silently merged into the results.

## Broad catalog results by skill

The following is the broad old-versus-current tuning sweep. A delta is the
automated required-grader pass-rate difference, not a human quality score.
The sweep was intentionally used to locate candidates and grader problems;
every decision is still `inconclusive` until the review and coverage gates are
complete.

| Skill | Paired trials | Invalid | Delta |
|---|---:|---:|---:|
| api-and-interface-design | 9 | 0 | +0.1111 |
| building-components | 9 | 0 | −0.2222 |
| cloudflare-deploy | 9 | 0 | +0.1111 |
| code-review-and-quality | 4 | 5 | +0.5000 |
| code-simplification | 9 | 0 | 0.0000 |
| debugging-and-error-recovery | 9 | 0 | +0.1111 |
| diagnosing-bugs | 5 | 4 | 0.0000 |
| grill-me | 9 | 0 | +0.1111 |
| minimalism-audit | 9 | 0 | +0.1111 |
| performance-optimization | 8 | 1 | 0.0000 |
| production-safety | 12 | 5 | 0.0000 |
| prototype | 8 | 1 | 0.0000 |
| receiving-code-review | 9 | 0 | −0.1111 |
| remotion-best-practices | 8 | 1 | 0.0000 |
| security-and-hardening | 15 | 0 | +0.0667 |
| shadcn | 17 | 8 | −0.1429 |
| source-driven-development | 9 | 0 | 0.0000 |
| systematic-debugging | 7 | 2 | +0.1111 |
| ui-quality | 9 | 0 | −0.1111 |
| vercel-composition-patterns | 2 | 7 | 0.0000 |
| vercel-react-best-practices | 9 | 0 | 0.0000 |
| verify-work | 15 | 0 | 0.0000 |
| web-design-guidelines | 4 | 5 | +0.5000 |

The largest apparent gains and losses are not decision-grade: they occur in
skills with invalid coverage or in cases where the grader is vocabulary-
sensitive. In particular, the apparent `shadcn` loss includes correct output
using `isDeleting`/`deleting` where a grader demanded the literal word
`loading`.

## Final targeted regression findings

After the focused hardening, the clean five-skill tuning run had complete
coverage and zero invalid trials:

| Skill | Paired delta | Interpretation |
|---|---:|---|
| api-and-interface-design | 0.0000 | Caller-identity hardening did not show a measurable automated lift in this small sample |
| production-safety | 0.0000 | Safety wording and offline gates were stable in the clean tuning set |
| ui-quality | +0.2222 | Strongest targeted signal, but only three cases and no completed blinded review |
| vercel-composition-patterns | 0.0000 | Harness false-positive was repaired; no lift shown |
| verify-work | 0.0000 | Raw outputs were bounded; graders still miss some equivalent evidence wording |

The 30-run post-tuning regression guard had no critical failures and no invalid
trials. It is a regression check, not a fresh acceptance holdout: it was run
after the initial frozen cases had already been inspected. Its current
automated result is therefore evidence of no obvious safety break, not proof of
generalization.

## Current all-catalog hardening cycle

The final candidate was then hardened across all 24 active skills. Every skill
received an explicit execution-boundary rule: text-only, plan-only, and
review-only tasks stay within supplied context; workspace-write tasks stay
within declared paths; and completion claims require observed evidence. The
systematic-debugging, React/Next, diagnosing-bugs, security, API, and web
guidance also gained focused output-shape requirements where tuning outputs
repeatedly omitted a required safety or diagnostic concept.

The final all-skill tuning matrix used 166 Luna-max attempts across all 24
skills. It produced 153 valid and 13 invalid attempts, with 70 of 83 planned
paired trials usable. On those valid pairs, baseline passed 46/70 (65.71%) and
treatment passed 50/70 (71.43%), a +5.71 percentage-point mean delta. The
case-clustered bootstrap interval was −2.86 to +14.29 points; outcomes were 7
treatment wins, 3 baseline wins, and 60 ties. The aggregate is therefore
exploratory and inconclusive because coverage was incomplete. Invalid attempts
were retained as invalid evidence rather than converted into task failures:
8 tool-boundary violations, 3 provider timeouts, and 2 evaluator-metadata
access attempts. No critical safety failure occurred in a valid paired arm.

The focused post-hardening tuning rerun covered API/interface design,
diagnosing-bugs, security-and-hardening, and web-design-guidelines with 56
additional attempts. Diagnosing-bugs showed the clearest targeted improvement:
the treatment produced the required labeled predictions in both falsifiable-
probe trials; API and web results remained noisy; security removed the earlier
allowlist omission without producing a measurable lift.

The frozen active-v2 holdout then ran once per skill, baseline and treatment:
48/48 arms were valid, all 24 pairs were complete, and there were no integrity
or critical-safety failures. Baseline passed 12/24 (50.00%); treatment passed
16/24 (66.67%), for a +16.67-point delta with a case-level bootstrap 95%
interval of +4.17 to +33.33 points. There were 4 treatment wins, 0 baseline
wins, and 20 ties. This is a positive regression signal, not a universal
acceptance claim: each skill has only one frozen holdout case, and deterministic
graders do not replace blinded qualitative review.

The current artifacts are:

```text
/tmp/skills-evals-catalog-tuning-final-20260818
/tmp/skills-evals-targeted-hardening-v2-20260818
/tmp/skills-evals-catalog-heldout-v2-final-20260818
/tmp/skills-evals-catalog-heldout-v2-final-20260818-<skill>
```

The last pattern contains the remaining per-skill frozen roots created to keep
the held-out output immutable. The API holdout is in the unsuffixed root; the
other skills use their suffixed root.

## What the data says about improving skills

The useful loop is:

1. Write a contract around a real user outcome, with a supplied fixture or an
   explicit missing-evidence case.
2. Add a known-good and known-bad artifact for every deterministic gate.
3. Run baseline and treatment in isolated, randomized arms.
4. Classify infrastructure failures and policy violations separately from
   quality failures.
5. Inspect paired raw outputs before editing the skill. If the output is
   semantically correct but fails on one word, repair the grader; if it omits a
   required safety boundary or produces an unsafe artifact, repair the skill.
6. Tune only on tuning cases. Lock a new, versioned holdout before making the
   next revision.
7. Use the smallest revision that addresses the observed failure, then rerun
   the affected skill plus a broad regression slice.
8. Accept a revision only after complete coverage, zero critical regressions,
   a meaningful interval, and blinded qualitative agreement.

This is why the current skill edits emphasize authorization boundaries,
evidence accounting, no invented context, offline behavior, and explicit
artifact checks. Those are durable behaviors; adding more keywords would make
the scores look better without making the agent more reliable.

## Remaining blockers before a “near-perfect” claim

1. The review packet directories contain packets but no completed human or
   independently calibrated reviewer scores. This prevents a decision-grade
   claim.
2. The original `evals/catalog/heldout.json` and its old skill-creator case
   remain intentionally preserved as historical evidence. They must never be
   used for a new acceptance claim; the active suite is `heldout-v2.json`.
3. Several early tasks intentionally lacked the files they described. Those
   are now useful missing-evidence tests, but they should not be mixed with
   artifact-production tasks in one quality score.
4. Most skills currently have only three to five independent tuning contracts.
   Hundreds of repeats of the same contracts would narrow sampling noise but
   would not solve the coverage problem. Add independent cases first, then
   increase trials where the decision remains close.

## Reproduction and validation

From the repository root:

```bash
python -m evals.v2.validate --suite catalog --root evals/catalog
python -m evals.v2.catalog_calibration
python -m evals.v2.reference_check
pytest -q evals/v2/tests
for skill_dir in skills/*; do
  python skills/skill-creator/scripts/quick_validate.py "$skill_dir"
done
python -m compileall -q evals/v2 skills/skill-creator/scripts
git diff --check
```

The final validation result was:

```text
37 passed
Contract validation passed: 107 cases across 24 skills.
Catalog grader calibration passed: 107 cases.
Reference check passed: 18 good/bad case pairs.
24 skills valid
```

Primary artifact roots for the latest reproducible runs are:

```text
/tmp/skills-evals-old-vs-current-tuning-v1
/tmp/skills-evals-old-vs-current-heldout-v1
/tmp/skills-evals-iteration-2-tuning-v2
/tmp/skills-evals-iteration-2-heldout-regression-v1
/tmp/skills-evals-iteration-2-skill-creator-tuning-v2
/tmp/skills-evals-iteration-2-skill-creator-heldout-regression-v1
/tmp/skills-evals-catalog-tuning-final-20260818
/tmp/skills-evals-targeted-hardening-v2-20260818
/tmp/skills-evals-catalog-heldout-v2-final-20260818-<skill>
```

The working tree is intentionally left with the hardened skills, the
contract-driven evaluator, and this report. No commit or co-author trailer was
created by this work.
