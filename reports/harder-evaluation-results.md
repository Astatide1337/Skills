# Harder skills evaluation results

Implemented on `feat/harder-skills-evals`, based on the completed lean catalog branch. No skill installation or global-instruction edits are part of this change.

## What the suite measures

Four synthetic Python standard-library repositories cover atomic tenant-scoped SQLite transfers with rollback/retry; pagination with strict transport, empty pages, cycles and bounds; cache cancellation/reentrancy and failure recovery; and public-contract compatibility repair. The last case is reserved as a holdout. These are bounded local engineering tasks, not a broad benchmark of real production systems.

Each uses a clean committed Git baseline, organic request, visible interface contract, runner-owned acceptance checks outside candidate files, and an unrelated tracked teammate draft. The current runner requires a clean disposable baseline; this suite does not establish preservation of initially dirty work. Golden implementations pass; originals, 11 semantic mutants, and weakened visible checks fail. Maintainability remains an independent review judgment rather than a fabricated numerical score.

## Validation

Catalog validation and Inspect task discovery passed. The full eval test suite ran 255 tests: 254 passed, one optional integration skip. The revised harder fixture/runner suite ran 11 tests successfully, also independently reviewed. No unresolved material review findings remain. Namespace prerequisite accepted. No behavior grader used.

## Pilot protocol

Two development cases, two repetitions per arm, eight actual native candidate calls maximum. Model `gpt-6.1-sol`, effort `low`; frozen current catalog and identical shared globals under `/home/sohamb/.cache/skills-harder-u4xfju9o`. Catalog content identity `7f8922b3155e2ec515defec1e43c78e013da7dace453e408da349287e2dd33ea`; globals identity `21900215a8dad4ad57544617267a1736f01d2fb1e9471890d0b3014b200c8c3c`. Current catalog versus explicit absent-catalog diagnostic measures marginal catalog contribution; it does not compare catalog revisions.

Two initial setup attempts produced eight unscored samples before any model call: missing Git baseline, then an unsupported initially dirty baseline. Both were retained in raw logs and fixed in the fixtures without weakening runner gates. Actual arms run in catalog-then-control order; order effects remain a limitation. Monetary cost and real human interruptions are unknown. Heldout case remains unexecuted and untuned.

## Live outcome

Both arms passed functional acceptance and workspace policy in all four runs. Runner acceptance exited zero in all eight actual native runs. The final-answer scorer is intentionally unscored because these cases have no constrained response format; independent raw-log review assesses claim support separately.

| Observation (four runs per arm) | Catalog | Catalog absent |
|---|---:|---:|
| Functional acceptance | 4/4 | 4/4 |
| Workspace policy | 4/4 | 4/4 |
| Completed command items | 30 | 26 |
| Agent message items | 14 | 12 |
| Uncached input tokens | 56,538 | 50,647 |
| Output tokens | 11,154 | 11,186 |
| Launch elapsed time, two concurrent samples | 3m36s | 3m30s |

These totals are recorded usage/proxies, not dollars or human effort. Output tokens are reported without adding reasoning tokens again. Zero aggregate failed-command items does not prove zero execution errors: raw logs include heredoc failures masked by later successful commands in a shell batch. Later checks executed successfully. Catalog runs show explicit coordinator reads; that does not establish use of every available skill or causal attribution to particular guidance.

Conclusion: this pilot shows no functional advantage from the catalog and modest additional observed process/input overhead. Eight runs on two synthetic problems are insufficient to establish a general cost or quality ranking. Keep the lean catalog unchanged rather than claim an improvement or add tools from this result. The suite increases regression pressure and validates the evaluation mechanism; it has not yet demonstrated marginal catalog efficacy.

Raw Inspect logs and a per-sample `summary.json` are retained under `evals/results/harder-pilot/`. Logs are ignored by Git; this report is the portable result.

## Next discriminating experiments

The first two development cases saturate this model at low effort. Stop at the declared eight-call budget. Next use authentic multi-file regressions where diagnosis spans caller, state owner and test fixture; intermittent failures with deterministic reproduction; and known-defect plus clean reviews that measure both missed defects and false positives. Add those only with explicit visible contracts and independent oracle controls. Execute the remaining cache development case in the next budgeted comparison before promoting guidance. Keep the compatibility holdout untouched until a candidate revision is selected. Do not tune on this pilot and then describe its cases as held out.

Change one guidance component per experiment, compare matched frozen arms, and retain it only for an observed gap without regressions. Optional tools need a separate capability-supported comparison; the local fixtures do not test browser, deployment, external service, or tool-integration performance.
