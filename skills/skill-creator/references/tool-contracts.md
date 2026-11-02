# Contracts for repeatable operations

Use this reference when adding or changing a tool, script or adapter. Reuse
native commands and result formats when they already meet the need.

## Before writing it

Identify the observed repeated error or costly operation. Inspect the native
command and owning tool first: read current help or authoritative metadata,
confirm the executable and target, and try the supported operation. Do not
invent flags, update commands or output formats from another CLI's conventions.
Automate an operation only after its inputs and effects are understood.
Keep product, architecture and aesthetic choices explicit rather than burying
them in a tool. Give one component responsibility for the interface.

For application CLI selection, authorized setup and keeping versions fixed
during a task, use
the [native-tool guidance](../../verify-work/references/agent-clis.md). Keep
package manifests and command semantics in the owning CLI project rather than
copying a permanent application revision into Skills.

In the operation's existing documentation, establish:

| Contract | What the agent needs to know |
| --- | --- |
| Inputs and prerequisites | Explicit target, source identity, supported versions, runtime and access |
| Effects | Processes, files, data and remote state it may change |
| Result | Observations and identity sufficient for the next decision, with links to detailed evidence |
| Failure | Failed stage, completed effects, unresolved state and supported recovery |
| Retry and interruption | Whether repetition is safe, how uncertain writes are inspected, owned cleanup |
| Limits | What success does not establish |

Use the native result format where adequate. Distinguish process exit, check
failure, application failure and unavailable capability. Missing required
observations are not a successful default. Avoid opaque success flags and
unbounded output. Do not silently install dependencies, use production as a
fallback or widen permissions to make a command succeed.

Preserve meaningful inner exits and stage results when an existing operation
launches subprocesses. An outer process that exits successfully after an inner
test failed has not produced passing evidence. Report the failed stage, target,
partial effects and recovery information; use
[`verify-work`](../../verify-work/SKILL.md) to decide what the observations prove.
Fix the owning result contract when possible instead of adding a second wrapper
that guesses success from log text.

## Exercise the actual interface

Run relevant valid, invalid, partial-failure, repeated-invocation and interrupted
cases in an owned environment. Check source/instance identity and evidence after
cleanup. Where isolation is claimed, exercise harmless owned permission canaries
through the actual execution path. A subprocess boundary does not establish
protection for browser, network or connected-app effects.

Then give the normal documentation to a fresh agent for an ordinary invocation
and a recoverable failure. Record what was exercised. Unit-test fixtures do not establish that a native
application or model interaction occurred. Fix a confusing tool interface
before assuming it needs more instructions.

## Adoption and maintenance

Review and test generated automation before relying on it. An implementer
cannot change the acceptance checker and immediately call its verdict
independent proof. Review that change separately, preserve the original
requirements, and test valid results and violations. Keep secrets and unrelated user data
out of examples and receipts. A checksum establishes identity, not correctness.

Keep the operation only when its benefit justifies maintenance and context cost.
Removal in favor of a better native tool is a successful outcome.

Anthropic's [tool-design account](https://www.anthropic.com/engineering/writing-tools-for-agents)
supports distinct capabilities, useful observations, actionable errors and
bounded results. It is evidence for those design choices, not a requirement to
copy its tools, response schema or evaluation infrastructure.

## Example and near-miss

A startup operation can report the specific application revision, dependency
versions, authentication mode, owned process identity and observed readiness.
That does not establish persistence, permissions or an end-to-end user journey.
A latency check can use a repeatable workload but must retain environmental
conditions and observed variation rather than promise identical numbers.
