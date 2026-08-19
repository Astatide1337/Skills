# Contract-driven Skills evaluations

This is the repository's evaluation path. The previous phrase/keyword
bootstrap evaluator was removed; no historical pass-rate report is used as
quality evidence.

The unit of evaluation is a task contract, not a keyword list. A contract
defines a realistic prompt, an isolated fixture, hard requirements, forbidden
outcomes, executable graders, and an anchored qualitative rubric. A trial is
valid only when the provider and harness complete successfully. A task passes
only when every required deterministic gate passes; critical safety gates are
never averaged away.

## Repository layout

```text
evals/
  pilot/                         # versioned pilot contracts and fixtures
  catalog/heldout.json           # preserved v1 frozen evidence (not active)
  catalog/heldout-v2.json        # active versioned held-out catalog
  v2/
    catalog.py                   # legacy-manifest adapter + catalog discovery
    schema.json                  # machine-readable contract shape
    validate.py                  # offline contract/fixture validation
    reference_check.py           # offline good/bad grader calibration
    graders.py                   # deterministic outcome and safety graders
    run.py                       # isolated baseline/treatment runner
    regrade.py                   # auditable deterministic regrade without reruns
    analyze.py                   # paired counts, bootstrap interval, decision
    analyze_catalog.py           # aggregate view clustered by skill/case
    catalog_calibration.py      # leave-one-grader-out offline calibration
    review.py                    # blinded human/LLM review packets
```

The pilot remains deliberately small: three calibration skills, six cases per
skill, four tuning cases and two held-out cases per skill. It is useful for
testing the harness and grader mechanics, not for making catalog-wide skill
decisions. Held-out cases must not be used to revise a skill after their first
scored run.

The full catalog suite is the scalable path. It normalizes the 24 existing
`skills/*/evals/evals.json` manifests as tuning cases without rewriting user
changes, and adds one explicit held-out case for every active skill. Validate
it with:

```bash
python -m evals.v2.validate --suite catalog --root evals/catalog
python -m evals.v2.run --suite catalog --dry-run \
  --skill api-and-interface-design --trials 3
```

After a catalog run, aggregate the completed skill directories with:

```bash
python -m evals.v2.analyze_catalog /tmp/skills-evals-catalog
```

The aggregate is exploratory. It clusters repeated trials by `(skill, case)`
and does not turn a one-case skill into a decision-grade result; each skill
still needs multiple independent contracts, qualitative review, and held-out
evidence before a revision is accepted.

The catalog currently contains 107 cases (83 tuning and 24 held-out). The
active held-out cases come from `evals/catalog/heldout-v2.json`; the original
`heldout.json` remains archived evidence and is deliberately not loaded into
the active catalog. The
legacy manifests are never copied into a treatment project, so a model cannot
read its own graders or expected outputs. Skills whose normal workflow needs
live docs, deployment credentials, or browser services are represented by
offline, bounded tasks here; this suite does not permit broad web search or
MCP access.

## Offline validation

Run this before any model call:

```bash
python -m evals.v2.validate
python -m evals.v2.reference_check
```

Validation checks the contract shape, unique IDs, anchored rubrics,
fixture/provider-context containment, reference artifacts, and obvious live
credential/endpoint leakage. For the pilot it also checks the six-case
composition. The reference check then
materializes every good/bad pair and runs the deterministic graders offline.
Neither command contacts a provider or the network.

## Evaluation run

After the task contracts and graders have been reviewed and the offline
reference check passes:

```bash
python -m evals.v2.run \
  --suite pilot \
  --skill production-safety \
  --provider codex \
  --model gpt-5.6-luna \
  --reasoning-effort max \
  --split tuning \
  --trials 3 \
  --workers 1 \
  --output /tmp/skills-evals-v2-pilot
```

When hardening an existing skill, create an immutable snapshot before editing
and pass its parent directory with `--baseline-skills-root`. The baseline arm
then receives `<snapshot>/<skill-name>` while the treatment arm receives the
current skill; omitting the option intentionally compares against no skill.
Do not mutate the snapshot during a run.

The runner creates a clean project and provider home for every arm/trial,
randomizes arm order with a recorded seed, copies the target skill only into
the treatment project, disables MCP/search configuration and provider network
access, invalidates observed shell network attempts (including denied package
registry requests), captures the full provider output and filesystem diff, and
grades the resulting state. Provider
failures and timeouts are reported as infrastructure failures; they are not
converted into zero-quality scores.

The provider sandbox is a defense-in-depth boundary, not permission to use the
network. Network-capable commands and denied network diagnostics are failed or
invalid trials. Codex does not expose a verifiable per-call tool allowlist in
this adapter, so requested tools are recorded and transcript/project behavior
is audited fail-closed; the run never claims that the allowlist itself was
enforced. The runner records actual skill, harness, and contract-suite digests;
analysis refuses missing or changed integrity metadata.

Use `--dry-run` to validate and print the planned trial matrix without making
provider calls.

The runner defaults to the four-case `tuning` split. Run the two frozen
`held_out` cases only after the skill and graders are locked, using
`--split held_out --acknowledge-held-out`; the explicit acknowledgement marks
the run as frozen evidence that cannot guide tuning revisions. Every run
records a contract-suite digest and analysis refuses changed contracts or
incomplete coverage. A real held-out run also creates `.held-out-lock.json` in
its output root; the runner refuses later tuning calls in that root and
requires a new empty root for another held-out run. `--split all` requires the
same acknowledgement, is available only for explicit exploratory runs, and
is never the default decision path.

## Analysis and review

```bash
python -m evals.v2.review /tmp/skills-evals-v2-pilot/production-safety/iteration-1
python -m evals.v2.analyze /tmp/skills-evals-v2-pilot/production-safety/iteration-1
```

`review.py` pairs each baseline and treatment output and assigns opaque arm
labels. Reviewers receive the task contract and artifacts but not the arm
identity. `analyze.py` reports exact denominators, invalid trials, critical
failure rates, per-case paired outcomes, a deterministic bootstrap interval,
and a predeclared decision only after a complete blinded review summary is
present. The point estimate and interval use the same
task-contract clusters; repeated trials are not treated as independent tasks.
It does not produce a single leaderboard score. `analyze_catalog.py` provides
an exploratory aggregate across skills and keeps one-case skill results
inconclusive.

No pilot or catalog result is considered decision-grade until the task/fixture contract
has a known-good and known-bad reference, the deterministic graders have been
tested against every required grader and its counterexample, and a human has
inspected the transcripts and a sample of blinded grades.

For catalog runs, the legacy tuning manifests are contract-adapted and held
out cases are checked structurally before provider calls. Catalog results are
still exploratory until the skill-specific reference artifacts and blinded
review sample are complete; a high pass rate alone is not proof of a better
skill.
