---
name: skill-creator
description: "Creates, revises, validates and evaluates agent skills with trigger tests and measured comparisons. Use when writing or changing a SKILL.md, skill description or skill eval."
---

# Skill Creator

Fix the observed problem with the smallest change that can address it. Claim
an improvement only when evidence supports it. Read
[measured improvement](references/measured-improvement.md) to compare quality,
overhead or performance on new tasks; [worked examples](references/worked-examples.md)
when adding teaching material; and [tool contracts](references/tool-contracts.md)
when automating a repeated operation.

## 1. Define the job

Before editing, identify:

- requests that should select the skill and nearby requests that should not;
- the behavior the agent needs help with;
- required tools, evidence and permitted actions;
- the target catalog and installation location.

Use the conversation, existing skill, recurring requests, corrections, failed
attempts and available tools. Ask for missing requirements only when they
cannot be found safely in those sources. The description should let a reader
predict when the skill applies, what it produces and where it stops.

Choose where to fix the problem using
[learn from repeats](../self-reflect/references/learn-from-repeats.md):

- Fix a one-off need in the current request or response.
- Put a cross-repository working default in personal or global instructions.
- Put project-specific behavior in repository instructions, configuration,
  tests or scripts. Enforce it in code when possible.
- Add a skill only for a distinct recurring task that needs focused guidance.

For a structural rule, identify the allowed pattern, forbidden alternative,
enforcing type, lint rule, runtime check or CI job, and a test that rejects a
violation. If judgment is still necessary, write one concise instruction
stating when it applies and what evidence to use. Do not repeat an enforced
rule as emphatic prose or create a skill for generic knowledge the agent
already handles well.

Use a temporary workspace for research, drafts and experiments. Follow the
[documentation boundary](../follow-instructions/SKILL.md#documentation-boundary)
when deciding what belongs in the project. A requested `SKILL.md` is a
catalog deliverable; adjacent documents need a separate purpose.

## 2. Design progressive disclosure

Every skill needs `SKILL.md` with YAML `name` and `description` fields.

Write the description for skill selection. Use third person to state what the
skill does, followed by `Use when` and the requests that should select it.
Use the user's likely words. Add a nearby non-trigger only to prevent a
collision. Keep the description on one line within the catalog validator's
[description budget](https://github.com/Astatide1337/Skills/blob/main/scripts/validate_catalog.py).
The body is unavailable until selection; procedure belongs there.

Good: `Drafts, opens, reviews or monitors GitHub PRs and GitLab MRs. Use for
any PR/MR task. Never merges.`

`Helps with pull requests` says too little. `When watching a PR` omits the
capability and other requests that should select it.

Keep the body to the workflow, decisions, required checks and reference links.
Assume a capable reader. Omit tutorials and motivational prose. Start with
`SKILL.md` alone, then add files only when they have a concrete job:

- Put detailed variants, schemas, domain rules and examples in one-level
  `references/` files linked directly from `SKILL.md`.
- Add tested scripts for repeated deterministic operations.
- Add assets needed for the result, with provenance and reuse permissions.

Do not add auxiliary READMEs, changelogs, installation guides or duplicate
summaries. A possible future audience or template is not a reason for a file.
Each Markdown file needs a reader, a condition for loading it, a decision it
helps make and a reason to remain separate. State that purpose in the file
and its incoming link, without maintaining a duplicate registry. Catalog
validation checks reachability through links and explicit inline paths; it
cannot prove usefulness. Keep historical evidence outside routine skill
loading and preserve its provenance.

Use lowercase hyphenated names under 64 characters. The directory name must
match the frontmatter name.

## 3. Set the right freedom

Use guidance when several approaches may be valid. Use an ordered procedure
when sequence or failure handling matters. Use a tested script when repetition
or fragile steps make prose unreliable.

Explain non-obvious constraints so the agent can apply them to new cases.
Avoid turning one example into the only permitted solution. Reserve absolute
language for requirements and safety boundaries.

## 4. Implement safely

For an existing skill, read its root file and the references relevant to the
change. Preserve user-authored material and provenance.

For a new skill, create only the files it needs. Run a representative safe
case for each bundled script. Do not include credentials, cookies, copied
session data, malicious behavior or unexpected external writes.

## 5. Validate structure

Run:

```bash
python skills/skill-creator/scripts/quick_validate.py skills/<name>
./scripts/validate-skills.sh
```

Package only when requested:

```bash
python skills/skill-creator/scripts/package_skill.py skills/<name> <output-dir>
```

## 6. Evaluate behavior with Inspect

Use the existing workflow cases and Inspect runner. Preserve the catalog's
primary-case invariant. Add cases only for changed behavior, and share them
across skills where possible. Do not build another runner, grader, viewer,
provider adapter or statistics layer. Teaching examples and their regression
tests are not held-out evidence.

An evaluation design must name the representative case, candidate guidance,
accepted baseline and behavioral evidence used for comparison. Keep task
inputs, model settings, tools, environment, permissions and budget comparable.
A no-skill control is an optional diagnostic, not a substitute for the
accepted baseline. Without that comparison, a case cannot show improvement.

Read [the evaluation procedure](references/evaluation.md) before execution.
It covers the existing Inspect tasks, authenticated native CLI, blinding,
effort settings and outcome and cost measurements. Keep expected answers out
of candidate prompts. Missing required output fails; preserve the stated
rules for artifact-only answers and unsupported environments.

For a design-only proposal, provide concrete repository commands for
structural validation and task discovery. Include a compact case specification:
input, hidden target behavior, candidate, baseline and comparison signal.
Inspect the repository before naming commands. Without a checkout, label the
expected command shape as unverified. Do not invent paths, task names, models
or automatic-routing settings.

## 7. Finish deliberately

- Check the description against requests that should and should not select it.
- Remove repeated or generic text and ensure every reference is reachable.
- Give the revised instructions to a fresh reader with a positive request,
  a nearby non-trigger and an attempt to skip a required check. Fix failures
  and rerun the same cases.
- Compare the result with the user's original request and corrections. Passing
  a fixture is not enough if the user's workflow remains unresolved.
- Report checks actually run and the limits of the evaluation evidence.
- Install, commit or publish only when the user requests that stage.
