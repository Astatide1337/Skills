# Engineering the Engineer v2 preview

Branch: `preview/engineering-the-engineer-v2`  
Source base: `52ef9c11fc6ac42e01bd6aed78ae15bf46250290`  
Status: implementation preview for a user-run project trial, not a demonstrated
quality improvement, protected runtime, or production release.

The [v2 design](docs/engineering-the-engineer-v2.md) is the design record. Its
proposal-status wording predates the user's subsequent implementation approval.
This branch does not change `main`, the global collaboration policy, the installer,
the app-CLI pin, or CI. It grants no merge, deployment, spending or automatic
rule-promotion authority. Application and runtime policies still apply.

## 1. Temporary project-local installation

For a new trial project on a Linux host with Git and Bash, these commands create
fresh directories and use the existing installer. They do not replace global
skills or overwrite an existing project. There is no additional service to buy.

```bash
set -euo pipefail
TRIAL=$(mktemp -d "$HOME/skills-v2-trial.XXXXXX")
git clone --single-branch --branch preview/engineering-the-engineer-v2 \
  https://github.com/Astatide1337/Skills.git "$TRIAL/Skills"
mkdir "$TRIAL/project"
bash "$TRIAL/Skills/scripts/install.sh" --all \
  --target "$TRIAL/project/.agents/skills"
cp "$TRIAL/Skills/global-instructions/AGENTS.md" "$TRIAL/project/AGENTS.md"
git -C "$TRIAL/Skills" rev-parse HEAD
printf 'Open a fresh agent session in: %s\n' "$TRIAL/project"
```

The copied policy is local to this fresh project. It is not installed in your
home or substituted for any existing application instruction. For an existing
application, use a disposable checkout and inspect its instructions first.
Do not overwrite an existing `.agents/skills` or `AGENTS.md` without preserving
and reconciling it. The existing installer replaces selected same-name packages.

Use the explicit local catalog, beginning at `.agents/skills/follow-instructions/SKILL.md`.
A suitable session instruction is:

> Use this project's preview catalog and AGENTS.md. Start with
> .agents/skills/follow-instructions/SKILL.md and load only relevant references.
> Do not install or edit global skills. Build the project I describe, using the
> agreed scope and quality standard. Inspect actual renders, verify real behavior,
> and obtain required independent review. Do not weaken acceptance, merge or deploy.

Confirm which same-named skills the runtime actually loads. A project-local
installation does not prove every harness excludes global or bundled skills.
When one-version routing cannot be confirmed, call it an exploratory trial,
not a controlled comparison. Stop that session to stop using the preview. Keep
project work and remove only the local trial skills when no longer needed.

## 2. Real visual references and documented AI failures

The [visual reference guide](skills/web-interface/references/composition-examples.md)
replaces the self-made illustrations. It includes Apple Music and Stripe payment
layouts, two documented weak AI-generated screens, and a better AI-generated
alternative. Each has source attribution, a concrete judgment and limits.
Linear's official design article is supplementary rationale. Its image was not
renderable in the final inspection pass, so it is not counted as visually verified.

For the local image-reading tool, fetch the selected public images explicitly:

```bash
python3 "$TRIAL/project/.agents/skills/web-interface/scripts/fetch_references.py" --list
python3 "$TRIAL/project/.agents/skills/web-interface/scripts/fetch_references.py" \
  --all --output "$TRIAL/reference-images"
```

The five images go into a fresh run-owned directory with an index and receipt.
Inspect the actual pixels. Network access is required for this optional operation,
not for skill installation. Download errors remain errors. The receipt records
bytes and failures, not an aesthetic score, signature, or redistribution license.
Third-party artwork is not bundled in Git or licensed for inclusion in a product.

[Sourced code failures](skills/code-review-and-quality/references/generated-code-failures.md)
cover disconnected interaction logic, route-order errors and redundant bookkeeping.
The sources explicitly identify AI-generated artifacts. We do not infer authorship
from disliked fonts, naming, or architecture. These are teaching cases, not a
blanket claim that AI output is bad or a hidden test set.

## 3. Design coverage

| Decision | Existing owner and implementation |
| --- | --- |
| One engineer, separate verification and improvement | `follow-instructions`, `verify-work`, `skill-creator` |
| Requirements differ from defaults and examples | `follow-instructions/references/engineering-judgment.md` |
| Stable operations use well-defined native tools | `skill-creator/references/tool-contracts.md`, existing CLIs, preview preparer and reference fetcher |
| Examples teach context and valid alternatives | `skill-creator/references/worked-examples.md`, sourced UI/code references and authorization controls |
| Separate design judgment, generation and fidelity | `web-interface/references/visual-direction.md` |
| Assess credible future changes, not folder aesthetics | `code-review-and-quality/references/maintainability-exercise.md` |
| Independently grounded expectations and current evidence | `verify-work/references/independent-acceptance.md`, with existing runtime boundaries retained |
| Check false rejection as well as false acceptance | `verify-work/references/authorization-example.py` and existing evidence checks |
| Improvement must transfer and preserve valid alternatives | `skill-creator/references/measured-improvement.md` |
| Preserve compatibility and authority | Existing catalog names, installer, globals, app-CLI pin and evaluator remain their owners |

No scheduler, gateway, new agent hierarchy, universal verifier, paid model ensemble
or unrelated application change is introduced. References explain methods. They
cannot enforce runtime isolation by themselves.

## 4. Comparison and rollback

For a qualitative trial, judge the actual artifact before its explanation. Keep
functionality, visual quality, usability, maintainability and relevant security
separate. A prettier but broken result stays unaccepted. Planned approval is not
the same as you diagnosing or repairing the agent's work.

The existing preparer can freeze committed baseline and candidate inputs without
activating them. From the preview checkout, choose a fresh output path:

```bash
python3 scripts/prepare-preview.py prepare \
  --baseline 52ef9c11fc6ac42e01bd6aed78ae15bf46250290 \
  --candidate HEAD --output /path/to/fresh-comparison
python3 scripts/prepare-preview.py verify /path/to/fresh-comparison
```

The source base above is not an assertion about your installed or last-accepted
configuration. Use its actual preserved identity when different. Snapshots are
inputs, not a sandbox or proof of honest execution. The manifest detects drift
relative to itself, not malicious edits to both the manifest and the files.

For controlled comparisons, follow the existing
[evaluation procedure](skills/skill-creator/references/evaluation.md) on a supported,
already-authenticated runtime. Inspect task discovery and namespace support first:

```bash
uv sync --frozen
uv run --frozen inspect list tasks evals/skills.py
python3 scripts/namespace-doctor.py
```

Use its existing `workflows` task with explicit candidate/baseline roots, the same
authorized model/settings, native tools, application inputs, acceptance and finite
budget. Include the targeted issue, ordinary work, an unseen related task, a case
where the new default should not apply, and another valid solution. Do not tune
on exposed cases and then call them held out. A namespace or runtime failure is
not permission to remove the support gate. A time budget is not a token quota cap.

If this preview does not help, keep the accepted version and diagnose the failed
decision. Change the responsible tool, context, method or evaluator rather than
accumulating rules or lowering the bar. Removal can be an improvement.

## 5. Checks and remaining evidence

The final targeted suite ran **34 tests successfully** in the authoring container:

```bash
python3 -m unittest evals.tests.test_preview_preparation \
  evals.tests.test_engineering_examples evals.tests.test_reference_fetching -v
python3 skills/verify-work/references/authorization-example.py
```

Tests exercise real disposable Git histories, snapshot drift and no-overwrite
behavior, installer resource copying, meaningful authorization controls, and
mocked HTTP success/failure/interruption handling. The installer bytes were
verified against the unchanged repository blob. Test inputs were reconstructed
from the changed-source bundle plus that installer, not a complete clone.
The reference-fetcher tests are not proof of origin availability.

Five external images were directly inspected through the web image viewer. Direct
network access from the coding container was unavailable. The Python fetcher's
live-origin path, a full-checkout catalog/suite run, independent agent review,
remote CI, real Linktree/Shrunk delivery and a model-quality comparison have not
been established by these targeted results. Do not report those as passed.

Run the unchanged full-checkout validation where supported:

```bash
./scripts/validate-skills.sh
uv run --frozen python -m unittest discover -s evals/tests -v
```

The first real-delivery milestone requires an actual requested application task,
current native/browser evidence, meaningful negative controls, independent review,
repairs and fresh-context repeatability. Linktree's documented CLI requires the
real local Shrunk dependency and explicit auth mode. Development login does not
prove CAS. Do not invent a defect or substitute a static demo for that delivery.
The later milestones require transfer and sustained work, not a branch or a
passing fixture count. Difficulty, breadth and authority advance separately.
