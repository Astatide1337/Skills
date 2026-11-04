# Local codebase knowledge

Use for substantial repository work that needs source flows, ownership,
contracts, tests or historical bug context. Discover and use existing local
knowledge first. If missing during authorized implementation, build a small application-local
wiki and use an existing open-source code graph. Read-only reviews and plans
use existing knowledge or source search; they do not install tools, start
daemons or create project files. Keep code and tickets authoritative; neither
wiki prose nor a graph hit establishes current behavior.

## Discover, then build only what is missing

1. Identify the application root and current revision (`git rev-parse HEAD`),
   dirty paths and relevant source hashes. Inspect `AGENTS.md`, `CODEOWNERS`,
   README/docs, entry points, tests and configured remotes. Search `.agents/wiki`,
   `.wiki`, `docs`, existing ADRs and graph configuration. Reuse an existing
   equivalent instead of creating competing ownership maps. Do not traverse
   credentials, secret stores, unrelated applications or generated dependency trees.
2. Create `.agents/wiki/index.md` if no equivalent exists. Keep brief pages for
   the flows actually needed: entry → caller → contract → side effect → tests.
   Record declared owners separately from inferred maintainers; never turn
   commit frequency into an ownership claim. Link authoritative documents and
   exact source lines at a full commit SHA. For dirty files add SHA-256 of the
   observed bytes and mark the citation as a working-tree observation.
3. Keep the entire private wiki out of publication by adding its root to the
   exclude file returned by `git rev-parse --git-path info/exclude`, preserving
   existing entries. This also works when a linked worktree has a `.git` file. First check
   whether any wiki files are already tracked; exclusion cannot untrack them.
   Never put private tickets into tracked pages. Use existing approved public
   documentation separately. Store rebuildable graph data under the excluded
   wiki's `cache/`. Ignored wiki pages may be absent from graph results: search
   them explicitly with `rg --hidden --no-ignore` scoped to that wiki root.
   Knowledge creation within authorized implementation needs no extra approval;
   publishing it remains a separate action.
4. Inspect the relevant source and tests before changing code. Use graph results
   to locate evidence, then open the exact source. Refresh after edits, branch
   changes and source/ticket updates. Missing graph hits require a coverage check
   and source search, not a conclusion that code or documentation does not exist.

## Tool selection and local operation

Default to [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp),
which supplies local Tree-sitter indexing, SQLite storage, CLI queries and
incremental updates without a hosted embedding service. Compare its fit with
[Joern](https://github.com/joernio/joern): Joern provides code property graphs
and Scala queries for deeper static/security analysis, but its documented JDK 21
runtime and analysis workflow add setup for routine source navigation. Select
Joern when that analysis is required; do not build another graph framework.
This is a fit decision, not a measured performance comparison.

The tested baseline is CBM `v0.12.1`, source commit
`a7158ac2f48ca646b4527341b76f930f2aeff87e`. For Linux amd64 use its
`linux-amd64-portable` release archive, SHA-256
`8c3d0341064301e78ecc84cf7348d4e2c6562a0f57448243ea560aaa34de36c1`.
The extracted binary SHA-256 is
`77745491f0a9c346d6da23eed4d92b5feaa31a27a883c9faa4fa9f47c8183705`.
These identify a tested artifact, not the latest release. Other platforms or
versions need their own compatibility smoke check.

Download the archive and its `.bundle` from that release. Verify the bundle
with Sigstore's GitHub verification command, constraining repository to
`DeusData/codebase-memory-mcp`, workflow to `release.yml`, and workflow SHA to
the full source commit above. Check the archive digest before extraction and
binary digest afterward. A checksum downloaded beside an archive alone does
not authenticate its publisher. Keep the verifier in task-local tooling.

For the pinned archive and downloaded bundle, the verified command is:

```sh
sigstore verify github --bundle "$BUNDLE" \
  --repository DeusData/codebase-memory-mcp \
  --sha a7158ac2f48ca646b4527341b76f930f2aeff87e \
  --cert-identity 'https://github.com/DeusData/codebase-memory-mcp/.github/workflows/release.yml@refs/heads/main' \
  "$ARCHIVE"
```

Inspect installation effects before running an installer; do not enable global
agent setup, hooks or model downloads as a side effect of indexing.

Use an absolute binary path and process-local `CBM_CACHE_DIR` and a unique
`CBM_RUNTIME_DIR`. Disable the UI in that isolated runtime before indexing;
the default daemon can expose a local HTTP API. Confirm the installed version
supports these controls before launch. CBM CLI uses
shared daemon coordination; a temporary daemon started by a one-shot call exits
when unused. CLI calls do not register a watcher. Do not kill another session's
daemon or change its cache configuration to resolve a conflict. Report the
conflict and use the existing compatible instance or a separately authorized
execution environment. Source details:
[CLI](https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/cli/cli.c),
[incremental pipeline](https://github.com/DeusData/codebase-memory-mcp/blob/v0.12.1/src/pipeline/pipeline_incremental.c).

After assigning `CBM` to the verified absolute binary and `APP` to the application:

```sh
export CBM_CACHE_DIR="$APP/.agents/wiki/cache"
export CBM_RUNTIME_DIR="$(mktemp -d /tmp/cbm-task.XXXXXX)"
"$CBM" config set ui_enabled false
"$CBM" cli index_repository --repo-path "$APP" --name application
"$CBM" cli list_projects --format json
"$CBM" cli query_graph --project application --format json \
  --query 'MATCH (f:Function) RETURN f.name, f.file_path, f.start_line, f.end_line LIMIT 20'
"$CBM" cli check_index_coverage --help
```

Use a short private runtime path to stay within Unix socket path limits. After
the CLI has released its temporary daemon, remove only that task-owned runtime.
Read the installed version's help before constructing coverage/search queries.
Indexing defaults to `persistence: false`; retain it to avoid exported snapshots.
Treat native symbol/call/doc relationships as observations, not runtime traces.
Keep the small ontology below in wiki records; native document indexing can
make pages discoverable, but arbitrary JSON records are not automatically
custom graph nodes. Hidden wiki coverage must be verified, not assumed.

The bundled [smoke check](../scripts/knowledge-smoke.py) takes `--binary` and a
new `--output` directory. It exercises actual CLI indexing/querying, source path
and line provenance, stale results before reindex, symbol replacement and file
deletion. It must isolate both cache and daemon runtime, disable the HTTP UI, and retain
subprocess output under its artifact directory. Run it
before adopting a different binary. It is a tool smoke check, not an evaluator.

## Compact ontology and freshness

Use JSONL records alongside short Markdown pages, without a second graph engine:

- Entities: `Flow`, `Owner`, `Contract`, `Test`, `Issue`, `PR`, `Bug`; code symbols
  keep the native graph's qualified names.
- Edges: `CALLS`, `OWNS`, `IMPLEMENTS`, `VERIFIED_BY`, `REPORTED_IN`, `FIXED_BY`,
  `REGRESSES`. Distinguish native static edges from human-supported assertions.
- Each record has `id`, `type` (or `from`, `relation`, `to`), `revision`,
  `sources`, `observed_at`, `confidence` and `status`. Every source identifies
  repository, full SHA, path and line interval; external sources use canonical
  issue/PR URL, update timestamp and the relevant comment/description location.
  For uncommitted source also store `content_sha256`. Confidence includes a reason.
- `status` distinguishes `observed`, `inferred`, `mined-candidate`, `reproduced`,
  `stale`, `unavailable`. Historical truths remain tied to their revision; they
  do not imply the bug exists at HEAD. Never attach a new SHA to old prose.

Before use, compare cited file bytes and revision with the working tree and
re-fetch a needed ticket's current metadata. Dirty same-SHA changes also invalidate
claims. Mark affected records stale and rebuild/recheck their dependency slice;
removed symbols invalidate dependent flows/edges. Unknown owners or inaccessible
sources stay unknown. Do not overwrite reviewed prose with generated guesses.

## Tickets and historical bugs

Read-only GitHub/GitLab retrieval is authorized in an implementation context.
Use configured `gh`/`glab` or a connected read-only API, selecting only relevant
issues, comments and PR/MRs. Start from the task, touched paths and nearby
history. Do not bulk-export private tickets, credentials or secret-bearing logs.
Redact unnecessary personal/sensitive fields before saving bounded excerpts.
Do not add a hosted index, embedding service or remote wiki publication.
Model context follows the user-authorized provider choices and applicable
repository data restrictions; knowledge tooling does not expand that access.

Mine fix/revert candidates with `git log` and PR/MR metadata, then inspect the
actual diff and linked report. Verify PR membership and merge SHA through the
host API; a title containing “fix” proves nothing. Keep one bounded record per
case with immutable parent/base and fix SHA, bug class, expected behavior,
reproduction command, source/test citations, PR/MR URL, explicit confidence and
results. Separate “report says fixed” from “reproduced before and after”. A
revert is a candidate until its failing behavior is demonstrated.

Replay a fixed independent regression against the parent and fix, preserving
fixture dependencies. Require a causal failure before and success after;
missing runtimes/files are setup errors, not reproduced bugs. Exercise an
alternative valid implementation and a clean negative with the same check.
Retain failed attempts and limitations. Do not count two fixes from one PR as
independent evidence that a workflow generalizes.

## Existing Inspect integration

Use `evals/skills.py::workflows`, existing `workspace-test` fixture contracts and
runner-owned `acceptance_test`; do not create another runner, grader or provider
adapter. Keep shared evaluator changes with the integration owner. Supply mined records and
execution-ready case data for integration into `evals/cases/workflows.json` or
the existing comparison cases. Put the bounded base source and public fixture
dependencies in `files`, restrict `allowed_paths` to implementation files, and
keep the acceptance regression in runner-owned metadata. Candidate-visible
checks are supplemental. Include stale knowledge as a challenge, but score source-inspection claims
from actual trace evidence separately; passing final-artifact checks cannot
prove the agent read the source. Preserve valid-alternative and clean-negative controls.

Discover tasks with `uv run --frozen inspect list tasks evals/skills.py`. Compare
explicit frozen baseline/candidate catalog roots using `workflows`' existing
`arm`, `case_ids` and root arguments under the existing namespace/permission
preflight. Use equal supported model/settings and budgets; keep hidden answers
outside candidate files. A deterministic historical replay proves the bug and
check, not guidance efficacy. Task discovery or case loading is not a completed
model comparison. Record unavailable execution honestly; never weaken isolation
or acceptance checks to obtain a result.
