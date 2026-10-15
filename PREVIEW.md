# Engineering Skills preview: native tools and complete delivery

Control for this revision: fetched `preview/engineering-the-engineer-v2` at
`233fb741431a41b22e865d9baaedf62a90bface9`. Candidate: the head of
`feat/native-delivery-judgment`. These are experimental instructions, not a
measured general improvement or permission to merge/deploy/install globally.
The original [v2 design](docs/engineering-the-engineer-v2.md) is historical design
context; current entrypoints and owners govern execution.

The October 13–15 audit found useful counterexample-driven reviews alongside
premature readiness, scope expansion and missed existing automation. Its actual
installed predecessor was `8f2d963`, not `52ef9c1`; installed preview package bytes
matched `233fb741`, while the actual user policy differed from source. Those
historical distinctions do not make the predecessor this revision's control.

## What to use

Start engineering work at `follow-instructions/SKILL.md`. Use its short path for
clear small corrections, and retain read-only boundaries for explanations/reviews.
`pull-requests` owns authorized delivery through current-head checks, review,
conflict resolution and host eligibility. A draft or ready flag is intermediate.
Explicit user/project design approvals remain binding; HTML is not a default gate.

Native tools own established operations. The [CLI reference](skills/verify-work/references/agent-clis.md)
explains discovery, task-stable identity, supported setup and limits for Agent
CLIs and Keelbox. T3 owns its collaborative browser and runtime continuation.
`create-workflow` is only for requested recurring automation, not an investigation
turned into a permanent harness. `skill-creator`, `unslop` and `deslop` retain their
distinct jobs. The duplicate custom playbook and obsolete internet-reach/Zen
bridge are removed.

Use the [three worked decisions](skills/follow-instructions/references/case-studies.md)
only when they address the task. They are original sourced instructional
exercises, not fabricated industry transcripts or behavioral-trial receipts.
The [visual collection](skills/web-interface/references/composition-examples.md)
has a task index, publisher attribution, actual-image access and limitations.
Images remain publisher-owned; no proprietary images/fonts are redistributed.
Open actual pixels, then check the implemented interaction through the browser.
A valid different design is allowed; copying a brand is not acceptance.

## Disposable installation and rollback

Use Bash/Git on an authorized Linux host. These commands install into two new
project directories, preserve the previous preview, and leave global skills and
application instructions unchanged. Resolve the candidate once before starting.

```bash
set -euo pipefail
trial_root=$(mktemp -d "$HOME/skills-preview-trial.XXXXXX")
git clone https://github.com/Astatide1337/Skills.git "$trial_root/Skills"
git -C "$trial_root/Skills" fetch origin feat/native-delivery-judgment
candidate_ref=$(git -C "$trial_root/Skills" rev-parse origin/feat/native-delivery-judgment)
git -C "$trial_root/Skills" worktree add --detach "$trial_root/control" \
  233fb741431a41b22e865d9baaedf62a90bface9
git -C "$trial_root/Skills" worktree add --detach "$trial_root/candidate" "$candidate_ref"
mkdir "$trial_root/control-project" "$trial_root/candidate-project"
bash "$trial_root/control/scripts/install.sh" --all \
  --target "$trial_root/control-project/.agents/skills"
bash "$trial_root/candidate/scripts/install.sh" --all \
  --target "$trial_root/candidate-project/.agents/skills"
printf 'Control: %s\nCandidate: %s\nRoot: %s\n' \
  233fb741431a41b22e865d9baaedf62a90bface9 "$candidate_ref" "$trial_root"
```

Supply the **same actual collaboration policy** to both fresh sessions and retain
application-specific instructions. Do not copy the candidate policy over an
existing application policy. Explicitly select one installed catalog, beginning
at `.agents/skills/follow-instructions/SKILL.md`; confirm actual loaded locators.
If global/bundled catalog isolation is unproved, report an exploratory trial.
Rollback: stop the candidate session and open the control project selecting its
catalog. Global restoration is unnecessary. Keep project work and evidence;
remove only explicitly identified disposable directories when finished.

Normal installation replaces selected same-name packages and does not prune
retired/unrelated packages. Preserve customizations before any selected install.
To retire a recognized old internet-reach in a disposable selected destination:

```bash
bash "$trial_root/candidate/scripts/install.sh" --retire internet-reach \
  --target "$trial_root/control-project/.agents/skills"
```

Retirement refuses changed/extra/linked/unknown content and leaves it untouched.
It is explicit, separate from installation and never runs on global targets here.

From a project directory, resolve the fetcher through the selected installed
skill, not relative to the source checkout:

```bash
python3 /absolute/project/.agents/skills/web-interface/scripts/fetch_references.py --list
python3 /absolute/project/.agents/skills/web-interface/scripts/fetch_references.py \
  --id linear-sidebar --id stripe-payment-layouts --output /absolute/fresh-reference-cache
```

Reuse that cache while its source URL/hash/container and decoder checks remain
valid. A fetched or decoded image is not proof of model inspection. Open it with
a vision tool; changed/corrupt caches fail visibly instead of silently replacing
observations. GOV.UK's live recovery example uses the documented browser path.

## Maintained checks and evaluation responsibilities

`./scripts/validate-skills.sh` is the one documented catalog-validation entrypoint;
it is a thin wrapper around `validate_catalog.py`, not another validation engine.
The optional evaluation suite owns offline tests and contained native comparisons.
`namespace-doctor.py` diagnoses evaluator prerequisites, not everyday work or
runtime isolation. `prepare-preview.py` snapshots committed comparison inputs,
detects drift and does not install, run, protect or resume agents. Their paths
remain stable because tests and snapshots consume them. `checkpoint.py` remains
a portable fallback when native persistence cannot retain acceptance; do not run
a second task ledger alongside a capable runtime.

```bash
./scripts/validate-skills.sh
uv run --frozen python -m unittest discover -s evals/tests -v
uv run --frozen inspect list tasks evals/skills.py
python3 scripts/namespace-doctor.py
python3 scripts/prepare-preview.py prepare --baseline 233fb741 \
  --candidate HEAD --output /absolute/fresh-comparison
python3 scripts/prepare-preview.py verify /absolute/fresh-comparison
```

When T3 exports `__PYVENV_LAUNCHER__` pointing at its AppImage, clear it for the
Python command (`env -u __PYVENV_LAUNCHER__ uv run ...`); otherwise subprocess tests
may report that AppImage as `sys.executable`. This does not change global settings.
Do not weaken evaluator boundaries to hide an unavailable prerequisite.

Use existing `workflows` task parameters with explicit control/candidate roots,
the same actual policy, model/effort/tools/permissions and a frozen finite budget.
Keep hidden expectations outside implementer write authority. Record every
failure/interruption, required human correction, observed calls and limits; no
cost estimate or uplift follows from a passing fixture. Native fixture resumption,
T3 thread resumption and real host delivery are different claims.

## Evidence for this revision

Targeted structural and installation checks, live installed-reference retrieval,
actual image viewing and native CLI setup have been exercised. Final offline
suite, bounded comparisons, T3 interaction/resume, independent review and host
readiness are recorded below when observed; pending work is not a pass.

### Observed validation (2026-10-15)

- Catalog: 22 skills, 22 primary behavior cases, 12 routing cases, 62 workflow
  cases. Complete offline suite: **263 tests passed**. An earlier full run failed
  the obsolete five-image assertion; it now checks six wired image references.
- Disposable install/retirement tests exercise both known historical packages,
  repeated retirement, preservation of modified/extra/linked content and unrelated
  skills. Actual installed-image retrieval from a project directory decoded and
  displayed Apple, Stripe and Linear pixels; reuse preserved hashes without a
  second download. T3 later rendered the GOV.UK example and its error link focused
  the missing year while retaining day/month.
- Real Agent CLIs source discovery found no releases, selected a development
  revision once, then used its frozen pnpm build/pack and documented npm prefix
  installation. Installed manifests matched artifacts. Linktree command discovery
  and help succeeded; invalid invocation and missing-run doctor retained exits
  2/4. Shrunk's usage path returned 4, not a fabricated successful help flag.
  Installed Keelbox's dev/unknown identity remained explicitly unproven; its help
  and missing-config doctor were inspected without starting a cluster.
- Fresh source review found an introduced cache symlink overwrite plus cancellation,
  comparison-policy and UI-approval contradictions. Corrections preserve an outside
  sentinel/prior receipt before any cache write, honor immediate cancellation,
  share one actual comparison policy and qualify explicit approval artifacts.

The finite budget is at most **12 control/candidate model turns**, including
resumed turns, plus at most three source-review rounds. Failed startup attempts
and interruptions are retained. Six Inspect turns used `gpt-6.1-sol`, high effort,
identical actual policy and fixture inputs, with existing protected acceptance.
Both arms corrected the small function (original failure then held-out success),
rejected stale passing evidence and accurately reported the missing external
receipt under local-only authority. No corrective user turn or extra approval
was required. Response-contract scores were deliberately unscored without a
model grader; those conclusions come from inspected outputs/commands. Automated
workspace policy passed in all six; the repair's behavioral acceptance passed.

| Three-case observed metric | Control `233fb741` | Initial candidate `dbef08f` |
| --- | ---: | ---: |
| Completed command events | 19 | 22 |
| Nonzero commands (expected failing checks) | 3 | 3 |
| Recorded uncached input tokens | 31,881 | 41,728 |

These are single observations across tiny heterogeneous fixtures, not cost,
speed or general quality estimates. They do not demonstrate improved performance.
The control/candidate policy hash was identical. Source-review corrections made
`76d2871`; they do not retroactively change the tested snapshot's identity.

Two held-back Inspect discovery attempts failed **before model execution** at
native metadata startup. A bounded model-free diagnosis returned `failed to
load AGENTS.md instructions for environment local: Permission denied`. Two T3
fallback requests then returned `provider_unavailable`/provider-status timeout
without accepting tasks. Neither result is passing transfer evidence, and no
permission, model or host security setting was weakened to make it pass.

The two installed-catalog UI fixtures are real local HTML/HTTP interactions, not
host PR simulations. Their authors opened the hash/source-matched Stripe pixels,
implemented distinct valid green/neutral and cream/navy settings layouts, and
exercised 422/409 retention, error-summary keyboard focus, viewer 403 with unchanged
server state, Cancel, valid save/reload and narrow viewport layout through T3.
The acceptance server/checker were outside the authors' write authority. T3's
full-access permission contract here is instruction-scoped, not OS containment;
the contained Inspect cases supply a different evidence boundary. Original
turns were really interrupted with pending checks and persisted acceptance; the
control's supported same-thread resume rechecked live state and completed the
released check. Candidate resumption and final source/host gates are pending
until their actual results are recorded. Explicit runtime resume is not proof of
automatic scheduling. No private transcripts or credentials are published here.
