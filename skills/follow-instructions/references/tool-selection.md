# Optional tools earn their place

The default uses the active harness's repository search/edit/shell/browser and
existing project checks. No additional service or adapter is required. Add a
capability only for an observed gap, with a native fallback and a removal rule.
Use one transport per capability: CLI behind a project command for analyzers,
MCP only when interactive documentation or semantic sessions justify it. Do not
expose a second shell/browser/file runtime through an adapter.

## Select the smallest useful addition

- Documentation gap: [Context7](https://github.com/upstash/context7), querying the
  installed library version. Choose CLI **or** MCP; official documentation is
  the fallback. The MCP release observed on 2026-10-12 was 4.3.0 (Oct 9); that
  does not identify the CLI package version.
- Semantic navigation gap: [Serena](https://github.com/oraios/serena), exposing
  symbols/references rather than duplicate file/shell tools or another memory
  system. Native search and language tooling remain the fallback. Observed
  release 1.7.0 (Aug 9).
- JS/TS removal candidates: [Knip](https://knip.dev/), calibrated to actual
  framework entrypoints before deleting anything. Existing compiler/linter and
  caller inspection remain useful. Observed 6.41.0 (Oct 9), Node 20.19+ or Bun.
- Accessibility gap: [axe-core](https://github.com/dequelabs/axe-core), integrated
  into existing browser checks. Keep keyboard and real interaction checks;
  a scan is not full accessibility proof. Observed 4.14.0 (Oct 5).

Specialists activate only for a named question: ast-grep for repeated syntax
transformations; fast-check/Hypothesis for consequential invariants; targeted
Stryker mutation trials for test effectiveness; variant analysis after a
confirmed recurring mechanism; zizmor for affected Actions; curated Semgrep,
Trivy, or kubeconform for the affected source/image/configuration boundary;
Scalene/Hyperfine for measured performance. Do not run broad scans or suites
merely because the tools exist.

Defer Repomix for ordinary repository-native work; bounded export to recipients
without checkout access is its distinct job. Prefer harness worktrees to
Worktrunk. Avoid complete overlapping planning, memory, browser, scanner, and
agent-runtime stacks. A current release alone is not a capability advantage.

## Pilot and maintain

Currency above is research metadata, not an installation pin, adoption claim,
or live integration result. Recheck official stable release, license, runtime,
and project compatibility immediately before a pilot. Pin the tested compatible
version; do not execute `@latest` on the normal task path.

For a trialed/adopted adapter, record its job, activation/exclusions, native
alternative, output evidence, tested version/date/license/runtime, scope,
network/credentials, fallback, config owner, and rollback condition in the
existing catalog/project configuration. Speculative candidates need no runtime
registry. Keep metadata out of routinely loaded skill roots.

Compare the simplified baseline with one marginal addition on representative
work. Keep only unique useful evidence or reduced effort that outweighs setup,
false positives, latency, context, and maintenance while preserving correctness
and authority gates. Test complementary pairs and removal when justified.
Optional failure falls back natively with a stated gap; it does not weaken a
required project check. Remove only trial-owned configuration, preserving
shared dependencies and secrets. Recheck on compatibility failures, security
advisories, or major harness changes rather than every task.
