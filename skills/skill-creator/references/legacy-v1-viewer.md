# Legacy v1 viewer workflow

This document is retained only for old workspaces that still use the original
viewer format. It is not an evaluation method for new work. Use the isolated
`evals/v2` runner, contracts, graders, and review packets for all current
quality decisions.

## Historical layout

An old workspace used a sibling `<skill-name>-workspace/` directory with
`iteration-N/eval-<name>/{with_skill,without_skill}/outputs/`. Creating a skill
used no skill as the baseline; improving one used an immutable pre-edit copy as
the baseline. Launch both arms for each case before comparing them.

## Historical review

The old flow stored `eval_metadata.json`, ran assertion checks, then generated
`benchmark.json`/`benchmark.md` and a browser review. Reviewers could inspect
the prompt, output, formal grades, and previous feedback. A submitted
`feedback.json` was the source of human comments. Empty comments were not a
substitute for a v2 qualitative review, and old pass rates must not be used as
acceptance evidence.

## Migration rule

When an old case or workspace must be preserved, migrate its intent into a v2
contract with a stable ID, explicit split, execution boundary, forbidden
outcomes, deterministic checks, calibrated good/bad references, and a
qualitative rubric. Keep held-out contracts frozen and never tune from their
results.
