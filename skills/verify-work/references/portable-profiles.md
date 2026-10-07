# User-owned verification profiles

Use when verification must travel with the user's tools and the application
repository cannot be changed. Reuse the application's existing checks or a
pinned application CLI. That CLI owns launch, readiness, instance identity,
domain operations, and cleanup; this helper does not replace those mechanisms.

Store a reviewed JSON profile outside the application checkout. It contains
`version: 1`, explicit relative `source_paths` relevant to the claim, and `steps`.
Each step has a unique `id`, `phase` (`start`, `doctor`, `drive`, `cleanup`),
literal argument-array `argv`, bounded `timeout` in seconds, and nonempty
`expect`: JSON pointers mapped to independently selected exact values. A
lifecycle profile orders start, doctor, drives, cleanup; an artifact-only check
can use a single drive. Captured source/workspace identity must remain unchanged through cleanup.

For example, a check step can be:

```json
{"id":"receipt-journey","phase":"drive",
 "argv":["node","/installed/app-cli.js","run","receipt-journey","--json"],
 "timeout":120,"expect":{"/summary/passed":true,"/cliVersion":"0.1.0"}}
```

Choose the application's actual invocation and output shape; the example does
not install or prove an available app CLI. Include doctor assertions for the
owned run identity and current application revision, and required check IDs or
exact check arrays so a removed check cannot satisfy only `/summary/passed`.
Declare additional inputs outside automatic content coverage, including every helper/script/config whose change could invalidate the claim.
Do not name credentials in source paths or put secret values in profiles.

Run from the installed skill directory:

```sh
python scripts/check_profile.py --profile /private/profile.json \
  --workspace /path/to/application --receipt /private/fresh-receipt.json
```

A fresh receipt is reserved before effects; accepted/failed/not-run steps and
source/profile identities are retained. Exit 0 requires all expected results
and unchanged captured inputs. Exit 3 retains a failed run; exit 2 reports an
invocation error. Failed or uncertain startup still invokes declared cleanup;
later drives stop after failure. Review cleanup authority before execution.
Receipts are private because command output can contain application data.
Timeout/cancellation cannot prove an ambiguous operation was rolled back.

Only use trusted commands with existing resource-ownership contracts. This is
an orchestration helper, not hostile-code containment, command authorization,
automatic dependency discovery, or proof that a command exercised the application. A command merely printing success supplies no application evidence.

## Workspace identity and reuse

Version-1 profiles accept optional `workspace_identity` with `mode` (`auto`,
`git`, or `artifact`) and `generated_paths` (bounded relative files/directories).
The default selects Git identity at a repository root, or declared-artifact
identity outside Git. A Git subdirectory/submodule is unsupported; explicitly
select artifact mode only for an appropriately bounded claim. Artifact mode
works without Git and never claims whole-workspace freshness.

Git mode captures HEAD (including an unborn revision), index entries/stages,
content hashes for recognizable source/config files, and nonignored untracked
sources. Dirty/index state is valid if unchanged during checks; a second edit
to an already-dirty source still fails. Other tracked/nonignored entries use
file metadata only. Credential-like paths and symlink targets are never read
for automatic content hashes. Ignored files, arbitrary data/config formats,
external dependencies and live application state are outside this coverage.
The receipt records these limits; add reviewed safe `source_paths` where needed,
never credentials. Metadata-only identity is conservative, not byte identity.
Git command failures do not silently downgrade a repository to artifact mode.

Declare legitimate generated output in `generated_paths` before execution.
These exclusions apply only to untracked entries; they cannot conceal tracked
changes or overlap declared sources. Ignored outputs are already excluded.
Exclude only app-owned generated artifacts, never untracked source inputs.
Intermediate changes observed between steps fail even if cleanup restores them;
changes made and restored wholly inside one command are not observable here.

Receipts now use version 2. Before reuse, compare the exact profile and current
workspace without executing its steps:

```sh
python scripts/check_profile.py --profile /private/profile.json \
  --workspace /path/to/application --check-receipt /private/fresh-receipt.json
```

Exit 0 means a previously passing receipt's captured inputs are unchanged;
exit 3 means stale/failed/old evidence, and exit 2 means inspection unavailable.
Rerun affected checks for changed inputs. Independently validate current
app-owned instance/revision/check identity before reusing a runtime claim.
Neither full workspace identity nor matching JSON expectations proves that a
command drove the app; meaningful app-owned operations and independently
chosen assertions remain necessary. This is an executable check when invoked,
not a universal agent completion gate.

For structured boundary regressions, compare independently chosen expected
JSON with actual output:

```sh
python scripts/boundary_checks.py json --expected /private/expected.json --actual /private/actual.json
```

For static CI references, use an interpreter with the catalog's pinned PyYAML:

```sh
/path/to/Skills/.venv/bin/python scripts/boundary_checks.py ci --dialect gitlab --file /path/to/pipeline.yml
```

Supported dialects are `github` and `gitlab`; undefined jobs and cycles reject.
Unresolved templates/includes/dynamic references reject as requiring platform
validation. Valid optional GitLab needs are allowed. This checks static job
references, not platform acceptance, stage/artifact semantics, or a remote run.
