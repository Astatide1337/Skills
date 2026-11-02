# Engineering Skills preview: native tools and complete delivery

This file records the **October 2026 preview comparison**. For installation,
use `main` and follow [README.md](README.md#install). Merging a source change
does not update installed skills or user and application instructions.

The historical control was `233fb741431a41b22e865d9baaedf62a90bface9` on
`preview/engineering-the-engineer-v2`. The candidate reached
`400df1a2cb7682117166219bd7cdd5a973e10fc4`; each trial below identifies the earlier
version it tested. Later receipt-validation fixes and promotion were not tested
in those model trials. Use current procedures for new work. These results do not
establish a general performance improvement or authorize merging, deployment
or global installation.

The October 13–15 audit found useful counterexample-driven reviews alongside
premature readiness, scope expansion and missed existing automation. Its actual
installed predecessor was `8f2d963`, not `52ef9c1`; installed preview package bytes
matched `233fb741`, while the actual user policy differed from source. The
comparison below still uses `233fb741` as its control.

## What to use

Start engineering work at `follow-instructions/SKILL.md`. Use its short path for
clear small corrections. Explanations and reviews remain read-only unless the
user authorizes changes.
`pull-requests` covers authorized delivery: checks on the current head, review,
conflict resolution and the host’s merge requirements. Creating a draft or
marking it ready does not complete those steps.
Explicit user/project design approvals remain binding; HTML is not a default gate.

Native tools own established operations. The [CLI reference](skills/verify-work/references/agent-clis.md)
explains how to find, install and identify a fixed version of Agent CLIs or
Keelbox, and what each tool can verify. T3 owns its collaborative browser and runtime continuation.
`create-workflow` is only for requested recurring automation, not an investigation
turned into a permanent harness. `skill-creator`, `unslop` and `deslop` retain their
distinct jobs. The duplicate custom playbook and obsolete internet-reach/Zen
bridge are removed.

Use the [three worked decisions](skills/follow-instructions/references/case-studies.md)
only when they address the task. They are original exercises based on published sources, not industry transcripts
or results from agent trials.
The [visual collection](skills/web-interface/references/composition-examples.md)
indexes examples by task and gives their publishers, image locations and limits.
Images remain publisher-owned; no proprietary images/fonts are redistributed.
View the actual images, then test the implemented interaction in a browser.
Other designs can satisfy the same requirements; copying a brand does not prove
the interaction works.

## Disposable installation and rollback

Use Bash/Git on an authorized Linux host. These commands install into two new
project directories, preserve the previous preview, and leave global skills and
application instructions unchanged. These frozen inputs reproduce the historical
comparison; they do not select the latest maintained catalog.

```bash
set -euo pipefail
trial_root=$(mktemp -d "$HOME/skills-preview-trial.XXXXXX")
git clone https://github.com/Astatide1337/Skills.git "$trial_root/Skills"
candidate_ref=400df1a2cb7682117166219bd7cdd5a973e10fc4
git -C "$trial_root/Skills" rev-parse --verify "$candidate_ref^{commit}"
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
at `.agents/skills/follow-instructions/SKILL.md`; confirm which skill paths the session loaded.
If you cannot show that global and bundled skills were excluded, label the trial
exploratory.
Rollback: stop the candidate session and open the control project selecting its
catalog. Global restoration is unnecessary. Keep project work and evidence;
remove only explicitly identified disposable directories when finished.

Normal installation replaces selected same-name packages and does not prune
retired/unrelated packages. Preserve customizations before any selected install.
To test retirement without changing the preserved control installation:

```bash
mkdir "$trial_root/retirement-skills"
cp -a "$trial_root/control-project/.agents/skills/internet-reach" "$trial_root/retirement-skills/"
bash "$trial_root/candidate/scripts/install.sh" --retire internet-reach \
  --target "$trial_root/retirement-skills"
```

Retirement leaves modified packages, extra files, links and unknown versions
untouched.
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

Use the existing `workflows` parameters. Name both catalog roots and hold policy,
model, effort, tools, permissions and budget fixed. Keep hidden checks outside
directories the implementing agent can write. Record failures, interruptions, human corrections, tool calls and limits. A
passing fixture alone says nothing about cost or improvement. Report native
fixture resumption, T3 thread resumption and real host delivery separately.

## Evidence for this revision

The following record covers structural and installation checks, reference
retrieval from an installed skill, image inspection, CLI setup, comparisons,
T3 interactions and resumption, independent review, and publication. Each result
applies only to the version and operation named.

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
- Fresh source review found that a cache write could follow a symlink and overwrite
  another file. It also found contradictions in cancellation, comparison policy
  and UI approval instructions. Corrections preserve an outside
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

These single observations from three small, different fixtures do not demonstrate
better cost, speed or quality.
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
full-access sessions relied on instructions to limit writes; the operating system
did not enforce those limits. The Inspect cases used a separate sandbox. The
original turns were interrupted while checks were pending, with acceptance
requirements saved. The control resumed in the same thread, rechecked state and
completed the released check. The candidate also completed supported same-thread resumption:
it recovered a lost process handle, established no duplicate checker was running,
reran the released check successfully, reopened T3 and verified unchanged artifact
and persisted form state. Both resumed without a corrective user instruction. The runtime was explicitly
told to resume them; this did not test automatic scheduling. No private
transcripts or credentials are published here.

The final source review independently reran 16 reference tests and four retirement
tests. It found one remaining unconditional HTML gate in a simplification leaf;
that leaf now delegates to the actual approval owner. Publication initially
failed because local DNS could not resolve GitHub. That failure was preserved;
network settings were not changed, and host readiness is established separately
from local checks.

After connectivity recovered, T3 accepted the same transfer requests without
creating duplicate tasks.
Both fresh discovery sessions correctly identified the effective configuration and
supported API from the offline snapshot, rejected the previous worker's unsupported
context/unlock advice, and explicitly left live authentication/reachability unproven.
Each used four command events; both fixtures remained unchanged. This was a held-back exploratory T3 case with identical policy, model and settings.
It was not a successful rerun through the Inspect sandbox. Total behavioral use was 12 model turns, including the
two genuinely interrupted initial UI turns and two same-thread resume turns; the
failed pre-model/native/provider attempts remain recorded above.

Final independent review at `4d48e577` returned no unresolved material findings and
independently passed 23 reference/installation tests. PR publication recovered
without changing network settings; the single review request targets the original
preview. Check GitHub for CI, approvals and mergeability on the final head; local results
do not establish them. The revision does not demonstrate general
agent-performance improvement; the available paired observations showed no such gain.
