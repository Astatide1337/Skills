---
name: skill-creator
description: Create, revise, validate, package, or evaluate a catalog skill when a repeated agent behavior needs focused, testable instructions. Not one-off or global rules.
---

# Skill Creator

Create the smallest skill that reliably changes agent behavior.

## 1. Define the job

Before editing, establish:

- concrete requests that should trigger the skill;
- nearby requests that should not trigger it;
- the behavior Codex needs help performing;
- required tools, evidence, and execution boundaries;
- the target catalog and install location.

Derive these from the user's real workflow before inventing an ideal one. Review
the current conversation, existing skill, recurring requests, corrections,
failed attempts, and tools actually available. Corrections are especially
valuable: they show where generic agent behavior diverges from the user's
expectations. Ask for missing success criteria or edge cases only when they
cannot be discovered safely from that evidence.

Design for lack of surprise. A user who reads the description should predict
when the skill activates, what authority it assumes, what artifact it produces,
and where it stops.

Choose the lowest layer that fixes the observed failure:

- current request or response for a one-off need;
- personal/global instruction for a cross-repository working default;
- repository instruction, configuration, test, or script for project-specific
  behavior that can be enforced there; and
- a skill only when a distinct recurring invocation needs focused guidance.

Do not create a skill for generic knowledge Codex already handles well. Do not
create or rewrite project documentation as a side effect of skill work; author
README files, AGENTS files, plans, or runbooks only when the user asks for that
artifact. A requested `SKILL.md` is the catalog artifact, not a reason to add
adjacent project docs.

## 2. Design progressive disclosure

Every skill requires `SKILL.md` with YAML frontmatter containing `name` and
`description`.

- Treat `description` as a routing instruction, not a miniature manual. Put
  the user situation that should select the skill first, then one or two nearby
  non-triggers when they prevent a collision. The body is unavailable until
  after selection.
- Good: `Use when the user asks to watch an already-open PR. Do not use to
  create one.` Bad: `Helps with pull requests and GitHub workflows.`
- Keep the body to essential workflow, decisions, safety gates, and reference
  routing. Assume Codex is capable; omit tutorials and motivational prose.
- Put detailed variants, schemas, domain rules, and examples in one-level
  `references/` files and link to each directly from `SKILL.md`.
- Add `scripts/` only for repeated deterministic operations that were tested.
- Add `assets/` only for files copied into outputs. Do not add auxiliary
  READMEs, changelogs, installation guides, or duplicate summaries.

Start with only `SKILL.md`. Add a reference, script, or asset only when a named
decision or repeated operation cannot stay reliable and lean in the root file.
A possible future audience, format, or template is not sufficient justification.

Use lowercase hyphenated names under 64 characters and keep the directory name
identical to the frontmatter name.

## 3. Set the right freedom

- Use guidance and heuristics when several valid approaches depend on context.
- Use a bounded procedure when ordering or failure handling matters.
- Use a tested script when repetition or fragility makes natural-language
  execution unreliable.

Do not encode one example so narrowly that the skill fails to generalize.
Explain the reason for non-obvious constraints so the agent can apply them to
new cases. Reserve absolute language for real invariants and safety boundaries.

## 4. Implement safely

For an existing skill, inspect its root file and only the references relevant to
the requested change. Preserve user-authored material and provenance.

For a new skill, create only the necessary directories and files. Validate any
bundled script by running a representative safe case. Never include credentials,
cookies, copied session data, malicious behavior, or surprising external writes.

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

Do not build a bespoke runner, grader, viewer, provider adapter, or statistics
layer. Add a small representative case to `evals/cases/catalog.json` only when
the skill teaches material behavior or resolves a meaningful routing collision.
Prefer shared cases over one suite per skill.

When asked to design an evaluation, the deliverable must name all four parts:
the representative case, treatment (catalog skill available), identical
baseline (skill absent), and the behavioral evidence or scorer used to compare
them. A case without the paired baseline is not an efficacy evaluation.

The repository task uses Inspect AI to run the locally authenticated Codex CLI
inside Codex's workspace sandbox. The treatment injects the selected catalog
skill verbatim and exposes its files; the baseline receives neither. This
isolates instruction efficacy from routing. Test installation and automatic
routing separately. Personal configuration and unrelated installed skills are
excluded. Inspect owns cases, concurrency, scorers, logs, and result viewing.

Validate task discovery without a model call:

```bash
uv run inspect list tasks evals/skills.py
```

Run the treatment and baseline only when the user authorizes model usage and
`codex login status` confirms a signed-in ChatGPT session:

```bash
uv run inspect eval evals/skills.py@catalog -T native_model=gpt-5.6-luna --max-samples 2
uv run inspect eval evals/skills.py@catalog -T with_skills=false -T native_model=gpt-5.6-luna --max-samples 2
```

Review transcripts and per-case scores in Inspect View. Look for qualitative
failure modes as well as the scalar grade: ignored instructions, unnecessary
steps, surprising authority, weak evidence, accidental overfitting, and user
corrections the rubric missed. A numerical win with worse interaction quality
is not an improvement.

Test trigger quality separately with positive, near-miss, and adversarial
requests. The behavior case measures what the skill teaches after injection; it
does not prove that the description routes correctly.

Do not tune on a hidden
case after observing it, treat repeated runs as independent tasks, or claim a
skill improved from a single noisy sample.

For a design-only skill proposal, finish with concrete repository commands for
structural validation and task discovery, plus a compact case specification
showing input, hidden target behavior, treatment, baseline, and comparison
signal. Do not leave these as “use the existing validator” or “add an eval.”
Inspect the repository before naming those commands. If the design task does
not provide a catalog checkout, give the expected command shape conditionally
and say it was not verified; do not invent paths, task names, models, or
automatic-routing settings.

## 7. Finish deliberately

- Re-read the description against positive and negative triggers.
- Remove duplicated or generic text.
- Ensure every reference is reachable from `SKILL.md`.
- Compare the result with the original conversation and corrections. Confirm
  that it solves the user's workflow rather than only passing the eval wording.
- Report validation actually run and limitations of any evaluation evidence.
- Install, commit, or publish only when the user requests that stage.
