# Harder Skills evaluation protocol

The question is whether catalog guidance improves engineering outcomes, not whether a model can solve a difficult puzzle. Use the existing Inspect workflow runner, native Codex solver, workspace containment, runner-owned acceptance checks, and final-answer/workspace scorers. Do not create a second provider or grading system.

## Controlled comparison

Compare `candidate` with a frozen prior catalog using `baseline`. Both arms get exactly the same organic request, project files, visible tests, native model, effort, global instructions, executable capabilities, and runner-owned acceptance expectations. The model receives project facts but not the golden implementation or acceptance snippets. Catalog availability/content is the treatment. Explicit `no-catalog-diagnostic` measures the marginal contribution of the current catalog against its absence. Use the prior-catalog arm when measuring a catalog revision; these answer different questions.

Freeze both catalog trees before launch, retain their commits and content identities, and use one shared global instructions file. The native solver snapshots loaded catalog bytes and records their identity. Sample metadata records the selected source content identity, global identity, requested model and effort. Provider internal settings are not observable beyond explicit CLI arguments.

The `harder_workflows` task requires explicit `native_model` and `native_effort`. By default it selects only `split=development` cases from `evals/cases/harder.json`. `case_ids` must belong to the selected split. Holdout selection requires explicit `split=holdout`; do not repeatedly tune against its outcomes. This is procedural separation, not encrypted secrecy: maintainers can read the fixture file.

Use Inspect epochs for repetitions, preserve every run and failure, and alternate arm order across launches where feasible. A small smoke comparison is evidence about those particular tasks, not a leaderboard or a general superiority claim.

## Existing runner entry point

```sh
.venv/bin/inspect eval evals/skills.py@harder_workflows \
  --model mockllm/model --epochs 2 \
  -T native_model=YOUR_EXPLICIT_NATIVE_MODEL -T native_effort=medium \
  -T arm=candidate -T candidate_skills_root=/absolute/frozen/candidate/skills \
  -T global_instructions=/absolute/shared/AGENTS.md
```

For the paired baseline, change `arm` to `baseline` and supply `baseline_skills_root=/absolute/frozen/baseline/skills`. Keep globals, model, effort, epochs, and selected cases identical. The outer Inspect model is a harness placeholder; the native solver executes the requested native model. These examples do not authorize unattended live runs or spending.

## Evidence and scoring

The prelaunch support gate applies to every case. Unsupported required capabilities or inability to observe the absence of any prohibited effect blocks the run; do not remove restrictions to obtain a pass. Workspace-delete observations come from actual workspace snapshots, not guessed command names. Passing workspace policy does not prove every possible intermediate effect was absent.

Objective scoring remains the existing `workflow_effects`, `workflow_final_answer`, and `workspace_policy`. The optional model behavior grader is off by default. Read the individual scorer outcomes and support status; do not turn blocked infrastructure into evidence of catalog weakness or hide genuine failed runs.

Report independently:

- Functional outcome: original failure, acceptance/regression outcome, and final artifact state.
- Scope and claims: preserved unrelated files and final claims supported by observed checks.
- Native effort: Inspect timestamps, recorded native input/output/cached tokens, completed/failed commands, and emitted agent-message counts.
- Guidance exposure: recorded catalog discovery and actual instruction access when observed. Installation alone does not establish that the agent read or followed a skill.
- Unknowns: real user interruptions, provider internal settings, monetary subscription cost, and unobserved effects. Command or message counts are proxies, not measurements of human friction. A shell batch can exit successfully after an earlier subcommand fails; zero failed command items does not establish zero execution failures.

Avoid an invented aggregate score or currency conversion. Inspect repeated scores provide the native summaries; small samples warrant case-by-case reporting. An improvement should survive multiple cases and repetitions without regressing safety or creating substantial unnecessary work. Add one catalog component at a time for a greedy trial, then run the broader development set before deciding whether to keep it. Run holdouts after decisions are frozen; any subsequent revision needs new holdouts.
