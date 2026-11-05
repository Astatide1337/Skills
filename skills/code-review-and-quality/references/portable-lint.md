# Portable correctness and strict type checks

Use this supplemental lint profile alongside the application's native build,
tests and user-flow checks. A pass covers only the reported files and context;
it does not verify architecture or runtime behavior. The profile does not
include React Doctor, React Compiler, JSX accessibility or general module-layer
rules.

## Explicit external setup and read-only doctor

Use Python 3.10+, uv, and Node 24+ (also Node 22.13+ on the 22 release line) with npm.
Choose a **fresh external directory** whose parent already exists:

```sh
python /path/to/skill/scripts/setup_portable_lint.py --runtime /external/new-runtime
python /path/to/skill/scripts/setup_portable_lint.py --doctor --runtime /external/new-runtime
```

`--language python` or `--language typescript` provisions/inspects only that
language. Without a runtime, `--doctor` checks prerequisites. Setup refuses
existing paths, writes an ownership marker, uses frozen npm integrity and Python
hash locks, disables npm lifecycle scripts and requires Python wheels. A failed
partial setup stays visibly incomplete; choose a fresh path after investigating.
Lint and doctor never install or repair tooling. Runtime files are trusted,
reviewed tooling; version/lock checks are not a malicious-runtime sandbox.

Pins: Ruff 0.16.10, Mypy 2.4.0, ESLint 10.12.0,
typescript-eslint 8.71.1, TypeScript 6.0.2, official Hooks 7.1.1.
Python transitive versions/hashes are in `assets/portable-lint/requirements.lock`;
JavaScript versions/integrity are in its `package-lock.json`.

The installer includes the `verify-work` helper required by
`code-review-and-quality`. It preserves an incompatible custom helper unless
you explicitly select its replacement. `--help` works even
when the helper is absent; an actual check reports that gap.

## Files, projects, and native configuration

```sh
python /path/to/skill/scripts/portable_lint.py --workspace /app \
  --runtime /external/new-runtime --receipt /external/new-receipt.json src/module.py
python /path/to/skill/scripts/portable_lint.py --workspace /app \
  --scope changed --base HEAD --runtime /external/new-runtime \
  --receipt /external/new-changed.json
```

`--language auto|python|typescript` defaults to auto. `--scope explicit` is the
default; provide unique regular relative files. `tracked` selects Git-tracked
files; `changed --base REF` selects differences plus nonignored untracked files.
`--base` selects files only. Git discovery requires the repository root.
Non-Git workspaces use explicit files or `directory --source-dir RELATIVE_DIR`.
Discovery reports each selected file's language, excluded or generated
directories, deleted or unmatched paths and missing context. An empty selection
is unavailable, not a pass. Supported selected files must be checked rather
than silently skipped. The tool rejects symlinks, paths outside the workspace
and paths that appear to contain credentials. Recognized generated/tool
folders are excluded from automatic discovery; explicitly requested regular
source files are still checked.

TypeScript/JavaScript uses each selected file's nearest native `tsconfig.json`
or `jsconfig.json`, actual references/membership, aliases, JSX settings,
module resolution, declarations and dependency context. `--project RELATIVE_FILE`
selects an existing config. Strict compiler flags are overridden in memory;
JS uses checkJs in memory. The tool does not create a fallback project, emit declarations, write a
tsconfig or install dependencies. Missing config/declarations/modules or
unsupported symlinks are unavailable. Existing reference outputs must be
provided by an independently authorized native build. Compiler findings can
include imported/nonselected files in the actual project.

Python uses an isolated, line-preserving snapshot of bounded `.py`/`.pyi`
source, keeping package layout and root/`src` import bases. Its context is capped
at 4096 project files/64 MiB and 20000 dependency/stub inputs. Native Ruff/Mypy
config and Mypy plugins are not loaded. `--python-executable FILE` selects the
trusted target interpreter for real installed imports; otherwise the tooling
interpreter is used. The pinned Mypy search query checks actual site/`.pth`
roots. If a root lies outside that interpreter's installed or standard
libraries, the tool reports it unavailable before reading its contents. It
records regular `.pth` files, interpreter configuration and the query helper
as part of the dependency identity. Custom import roots, generated or omitted
modules, missing stubs or dependencies and unsupported layouts need a known
context; otherwise the check remains unavailable. Python without `--runtime` still works
when its executing environment
contains both exact pinned tools.

## Actual checks and suppressions

Ruff uses isolated `F,B012,B018`, no cache and ignore-noqa. Mypy uses isolated
strict mode, no incremental cache and actual target-interpreter dependencies.
The snapshot blanks `# type: ignore...` and `# mypy:...` comments, preserving
lines/columns and ordinary type comments; imported project source is included.
Deliberate casts and inaccurate annotations/type guards can still pass.

The reviewed typed ESLint set is: no-floating-promises (bare void does not waive
handling), no-misused-promises, no-unsafe-assignment, no-unsafe-return,
no-unsafe-type-assertion, switch-exhaustiveness-check (default does not waive a
missing union case), no-explicit-any, no-unsafe-call, no-unsafe-member-access,
no-unsafe-argument, await-thenable and no-non-null-assertion. The changing
strictTypeChecked preset is not inherited wholesale. The Hooks plugin adds rules-of-hooks
and exhaustive-deps; compiler-recommended React rules require separate review.
JS/JSX still receives applicable lint/Hooks findings when a required typed stage
is unavailable. ESLint uses allowInlineConfig:false, no app ESLint config and no
bulk suppression file. Native TypeScript suppression directives are explicitly
rejected; original source is preserved, not stripped or autofixed.

Receipts version 2 record tool/profile identity, selected coverage, actual
source/config/import/dependency inputs, raw checks/diagnostics, per-stage
accepted/failed/unavailable and unchanged inputs. The existing verifier owns
process-group timeouts; private external temporary files carry raw lint output
up to 16 MiB rather than truncating it to the 64 KiB JSON envelope. Results remain
outside target/baseline; existing receipt paths are refused. Exit 0 accepts only
the stated scope; exit 3 retains failure/unavailability; exit 2 is invocation
failure. Old receipts can be displayed but cannot prove this stronger profile.
Checks do not autofix source, write target configuration or caches, or install
dependencies.

## Compare independently selected snapshots

```sh
python /path/to/skill/scripts/portable_lint.py --workspace /current \
  --mode compare --baseline-workspace /pre-change --runtime /external/new-runtime \
  --receipt /external/new-comparison.json src/module.py
```

Use independently selected separate workspaces with the same profile/tools and
unchanged nonselected import/config/dependency context. New files receive full
checks; deleted files are reported by discovery. Native checks remain required.
Raw full failures remain visible in `full_passed`, checks and diagnostics even
when incremental comparison accepts existing debt. The comparison matches each
diagnostic occurrence once by rule, message,
mapped location and unchanged source span. New duplicates and edited or
ambiguous spans remain new or changed. Unique unchanged lines can match after
a move. This identifies matching source, not who introduced it.

Parser failures, missing dependencies, mismatched tools or context, changed
inputs and unavailable baselines cannot be classified as preexisting debt.
Run a full check when the context changes.
Integration tests invoke real locked tools; missing prerequisites fail rather
than skip. Use `SKILLS_LINT_RUNTIME=/external/new-runtime` for repeatable tests.
