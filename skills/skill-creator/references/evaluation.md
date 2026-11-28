# Evaluate behavior

Use this procedure to design or run a skill evaluation with the repository's
autonomous evals (`evals/run.py`, `evals/grade.py`, cases in `evals/cases/`).

## Freeze the comparison

Before running, fix the cases, the baseline and candidate refs, the model, the
sample count and the budget. Both arms use the same model, container image and
cases; only the catalog differs. Do not switch models after a failed launch.
The accepted baseline is the current `main` catalog; a `none` arm is an
optional diagnostic of whether the catalog helps at all.

Runs use the Claude subscription named by the token and share its five-hour
usage limit with the owner's own sessions. Estimate the run count before
starting and keep concurrency low. A run that ends in an API error (usage limit,
outage) is infrastructure, not agent behavior: the runner leaves it unfinished
so a rerun repeats it. Never grade it.

## Write cases

Derive cases from observed agent failures. Each case is a directory with:

- `case.yaml`: `project` (an ordinary project name), `brief` (what a user would
  actually send), optional `turns` (later user messages), optional `setup`,
  hidden `checks`, and `assertions` split into `critical`, `required` and
  `overreach`, plus `accepted` alternatives.
- `repo/`: the fixture project, committed exactly as authored.
- `checks/`: scripts copied in only after the agent stops.
- `reference.patch`: a valid fix. `evals.tests.test_autonomous_cases` requires
  every case to fail a hidden check without it and pass all checks with it.

Keep evaluation cues out of everything the agent sees: no rubric, arm names,
expected routes or words such as eval, judge or rubric in paths or prompts. Do
not ask the agent to list the skills it used; the grader reads which skill files
the trace opened. Include ordinary tasks and genuine changes of direction, not
only traps, so the evals reward judgment rather than stubbornness.

## Calibrate before comparing

Apply [instrument validity](../../verify-work/SKILL.md#validate-the-measuring-instrument)
before treating a score as evidence. Label several traces yourself and check
that the judge agrees; check that planted defects fail and valid alternatives
pass. Change the evaluator and the candidate guidance in separate steps.

## Judge outcomes before cost

Read `grading.json` evidence and the traces behind surprising verdicts, not just
`benchmark.json`. A critical failure zeroes the run. Lower time or tokens never
compensates for a failed required check. Pairwise wins count only when the judge
prefers the same run in both presentation orders.

Three samples per case and arm is the minimum for variance to mean anything.
Treat a candidate as better only with a consistent pairwise win rate across at
least 15 decided comparisons; otherwise report no demonstrated difference, and
the smaller catalog wins. Stop at the declared budget and report inconclusive
results as inconclusive.

Read [measured improvement](measured-improvement.md) for baseline selection,
held-out tasks and adoption. A passing evaluation does not authorize adopting a
change; that is a separate decision by the owner.
