# Portable correctness lint

Use for affected Python or TypeScript files when you need supplemental checks
without changing the application repository. Skills owns these cross-repository
profiles; an app CLI owns its app's build, domain checks and running resources.
Run native lint/type/format checks too. This supplement proves neither type
correctness nor architectural boundaries nor the user journey.

Python checks use pinned Ruff 0.16.10: `F` (Pyflakes), `B012` (control flow in
finally can hide exceptions) and `B018` (useless expressions). TypeScript uses
pinned ESLint/typescript-eslint with type information to reject floating and
misused promises, unsafe `any` assignment/return, narrowing casts and omitted
union cases in switches (a default fallback does not hide a missing case).
A bare `void` does not prove rejection handling. Explicit
catch/await/return can be legitimate; review the actual error semantics.
Promise rules target unchecked side-effect/lifecycle risks. The additional
type rules are a P-stack-inspired construction standard, not a claim that each
historical incident was caused by a cast. Narrowing/unsafe-data checks come
from [typescript-eslint](https://typescript-eslint.io/rules/no-unsafe-type-assertion/);
missing-case checks use [switch exhaustiveness](https://typescript-eslint.io/rules/switch-exhaustiveness-check/).
A lying custom type guard can still pass: run allowed and malformed-input
regressions. Lint cannot prove a schema or detect every cancellation race.

Setup is explicit and installs only into Skills/user tooling. From the Skills
checkout run `uv sync --frozen` for Python. For TypeScript, reuse a reviewed external runtime with the pinned versions.
If absent, choose a fresh external runtime directory, copy `assets/portable-lint/package.json` and
`package-lock.json` from this skill there, then run:

```sh
npm ci --prefix /absolute/external/runtime --ignore-scripts --no-audit --no-fund
```

Do not overwrite another runtime or install into the application. Node 24+
recommended (Node 22.13+ on the 22 line also supported). The lock includes exact versions and integrity; this is a reviewed
trusted runtime, not a defense against modified installed packages.

Run with the Skills Python environment (replace these paths):

```sh
/path/to/Skills/.venv/bin/python /path/to/skill/scripts/portable_lint.py \
  --language python --workspace /path/to/app --receipt /private/new.json module.py
/path/to/Skills/.venv/bin/python /path/to/skill/scripts/portable_lint.py \
  --language typescript --runtime /absolute/external/runtime \
  --workspace /path/to/app --receipt /private/new-ts.json src/module.ts
```

Supply explicit regular relative files, never directories. TypeScript requires
an existing root `tsconfig.json` and project membership/dependencies; parsing or
missing-tool failures are unavailable/failed checks, never passing skips. This
initial profile does not support arbitrary monorepo layouts. Do not invent a
new app tsconfig merely to make it pass.

The supplement ignores inline suppressions and app lint configuration so they
cannot conceal these findings. Native checks retain their own configuration.
Install `verify-work` alongside this skill: its existing process/receipt helper
owns command execution. Integration tests use the real tools: with no supplied
`SKILLS_LINT_RUNTIME`, they install the locked npm tools in a disposable external
directory and fail if Node/npm/network prerequisites are unavailable.

No autofix, cache or config writes; existing receipt paths are refused. Receipts
are private and include tools, selected source hashes and raw diagnostics.
Exit 0 means these selected checks passed on unchanged declared files; exit 3
retains failure/unavailability, exit 2 is invocation failure. Imported files,
nested configs and generated types are not all fingerprinted: rerun after
relevant changes, and use native project checks for broader claims. Existing
project debt is a finding, not permission to rewrite unrelated files. Do not
weaken or remove a rule to claim a defect repaired.

Dependency boundaries need the project's actual ownership map and allowed
imports. No universal layering rule or style policy is installed here.
