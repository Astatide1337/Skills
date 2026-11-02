# Compare proposed improvements

Use this reference to assess a proposed instruction, example, tool or workflow
change. It covers experiment design; [evaluation](evaluation.md) covers running
and isolating the existing evaluator.

## Two separate decisions

Judge the delivered result and the proposed method separately. A better method
may still produce unacceptable work; a good result does not prove the new
instruction helped. Assess required functionality, appearance, usability,
security and maintainability separately. Lower cost cannot compensate for a
failed requirement.

## Diagnose and predeclare

Inspect actual attempts and locate the first wrong decision that affected the
result. Determine whether the cause was unclear requirements, missing context,
poor design, confusing tools, the environment, the evaluator or model capability.
Fix the responsible component before adding instructions. In the existing change
record, state the suspected cause, proposed change, comparison inputs, budget
and result that would make you revert it.

Prefer a small correction that helps related tasks and is practical to maintain.
Required safety and acceptance checks still apply. A frequent cosmetic issue
does not outrank a serious untested safety failure. If local fixes have stalled,
consider a different design or a limited sequence of prerequisite changes.

## Controlled comparison

Freeze the accepted baseline and candidate guidance, task and starting artifact,
model and effort, tool versions, environment, permissions, grader and run budget.
Use current authorized model choices, not a name copied from historical examples.
Vary the intended intervention. Model/runtime changes are separate experiments.
A simpler-guidance control can be useful but must retain required boundaries.
The no-catalog control is not the accepted baseline.

Use the existing Inspect workflow tasks for supported cases. Include:

- the targeted failure with the original observable requirement;
- a genuinely unseen related task or context;
- ordinary regression work, including an eligible tiny task;
- a case where the new default should not apply;
- a different valid implementation or visual direction that must not be rejected.

Known teaching examples and their tests are diagnostics. Reserve assessment
cases before tuning, track exposure and refresh them once they influence work.
Do not reward a required sequence of tools unless that ordering is itself a
real constraint. Accept equivalent solutions. For visual judgments, hide
origin labels where possible and inspect the artifact before the author's
explanation. Allow verdicts that neither candidate is acceptable, that reviewers
disagree or that evidence is insufficient.

Repeated runs estimate variation, not independent task coverage. Retain failures,
interrupted attempts, unavailable results and shared setup failures. Do not retry
one arm until it wins. Keep setup, implementation, repair and review effort
visible. Record planned approvals separately from user interventions needed to repair
an agent's work. Do not equate
tokens, elapsed time, quota use and money without the actual conversion.

## When results do not improve

| Observation | Action |
| --- | --- |
| Better outcome, required quality met | Propose adoption with scoped evidence |
| Better but still below the bar | Preserve progress, keep the artifact unaccepted |
| Same quality, justified lower overhead | Consider simplification without weakening required boundaries |
| No reliable benefit or regression | Retain the accepted baseline, revise the hypothesis or remove the change |
| Good work rejected, bad work accepted | Independently repair and recalibrate the judge, then reassess both arms |
| Shared environment failure | Repair the supported environment before attributing a difference to Skills |

Preserve the strongest candidate and failed evidence. A new attempt needs new
information or a materially changed method. At a real budget or permission
boundary, retain an unresolved result. Do not lower the standard or add a new
rule merely to make the experiment end positively.

## Promotion

Nothing is promoted automatically. A catalog change must answer an observed
failure (two distinct occurrences, or one on a safety boundary), use the
strongest enforcement that works per
[learn from repeats](../../self-reflect/references/learn-from-repeats.md), and
belong in the catalog rather than one application. Record declined proposals
with their reason in the existing proposal PR or issue. Adoption requires a useful gain or lower overhead, no observed material
regression in required capabilities and an explicit authorized decision. Permission and verifier changes cannot be justified
by an aggregate score alone. Deletion is a valid improvement. Reassess methods
when models, tools or the workload change.

Do not impose universal 30-task, 90-percent or four-week thresholds. Predeclare
criteria suited to the actual workload and report raw counts and limitations.
