# Older versus newer skills: controlled evaluation

This evaluates the complete old catalog against the lean replacement, using the existing harder Inspect task. It does not compare against absent skills or attribute outcomes to individual skills.

## Frozen comparison

- Older catalog: commit `52ef9c1`; all 124 snapshot files verified against Git. Content identity `2e76cb5510a2135d186f67e51458c0fb99b49f3c0d608deac4e7f2a277d8cfe6`.
- Newer catalog: commit `86f7d38`, unchanged on the harder-evals branch. Snapshot and current repo identity `7f8922b3155e2ec515defec1e43c78e013da7dace453e408da349287e2dd33ea`.
- Shared global instruction identity: `21900215a8dad4ad57544617267a1736f01d2fb1e9471890d0b3014b200c8c3c`.
- Native model `gpt-6.1-sol`, effort `low`, native binary 0.162.1; identical tools, organic requests, clean Git fixtures and hidden acceptance. No model behavior grader.
- Budget: eight actual native trials; ledger atomicity/retry and cache cancellation/reentrancy, twice each per catalog. Order old→new then new→old, two concurrent samples per launch, 480-second sample time limit. No tuning between repetitions. Compatibility holdout untouched.

Focused 11 fixture/runner tests passed again and namespace prerequisite accepted before launch. These local synthetic tasks do not measure production integrations, initially dirty-work preservation, or general engineering ability.

## Outcome

Eight actual native trials completed without launch errors or blocked samples. Both catalogs passed the hidden functional acceptance and workspace policy on both cases in both repetitions. Runner acceptance exited zero in every trial.

| Observation, four trials per catalog | Older | Newer |
|---|---:|---:|
| Ledger functional acceptance | 2/2 | 2/2 |
| Cache functional acceptance | 2/2 | 2/2 |
| Workspace policy | 4/4 | 4/4 |
| Completed command items | 23 | 26 |
| Agent message items | 12 | 12 |
| Uncached input tokens | 57,592 | 62,618 |
| Output tokens | 7,761 | 8,579 |
| Sum of launch elapsed times, two concurrent samples | 3m00s | 3m12s |

The newer arm used approximately 8.7% more uncached input tokens and 10.5% more output tokens in this sample. These are recorded observations, not stable cost estimates: cache state, stochastic behavior, test construction and command batching vary. Currency cost and real human interruptions are unknown. Output tokens are reported without adding reasoning tokens a second time.

Aggregate failed-command items were zero older and three newer. Those counts include negative reproduction checks and are not engineering-failure scores. A shell batch can also mask a failed subcommand behind a later successful command, so zero does not prove no execution errors. Functional outcome remains the primary gate.

Raw logs show coordinator reads in all trials. Some newer trials additionally accessed verify-work or systematic-debugging guidance; exposure varied between repetitions. Neither exposure nor a green outcome establishes faithful application of every catalog procedure or identifies a particular skill as the cause. No candidate claimed a returned independent review. External review of raw artifacts and executed checks supports the narrow outcome claims.

Final-answer scorer is unscored because cases do not impose a constrained response format; it is not counted as a pass. Raw logs and per-sample summary are retained locally under `evals/results/revision-pilot/`.

## Decision

There is no demonstrated quality winner. The older catalog had modestly lower observed overhead on this eight-trial comparison; the newer catalog did not demonstrate better execution efficiency here either. This is insufficient evidence to rank the catalogs generally, revert the lean redesign, or rank individual skills. Source brevity has not automatically translated into lower runtime token use.

Keep the catalogs unchanged from this experiment. The measured correctness ceiling is saturated again; the next useful work is more discriminating authentic multi-file diagnosis and calibrated defect/clean reviews, followed by one-component ablations when a gap appears. Do not spend additional repetitions on these already-solved fixtures merely to hunt for a favorable result. The compatibility holdout remains untouched.
