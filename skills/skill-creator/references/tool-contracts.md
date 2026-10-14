# Contracts for repeatable operations

Use when adding or changing a tool, script or adapter. This is not a mandate to
wrap native commands or create a universal result schema.

## Before writing it

Identify the observed repeated error or costly operation. Inspect the native
command and owning tool first. A stable operation can move into code only when
its inputs and intended effects are understood. Product choices, architectural
trade-offs and aesthetic judgments must not be hidden in a supposedly neutral
tool. Choose one owner for the changing contract.

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

## Exercise the actual interface

Run relevant valid, invalid, partial-failure, repeated-invocation and interrupted
cases in an owned environment. Check source/instance identity and evidence after
cleanup. Where isolation is claimed, exercise harmless owned permission canaries
through the actual execution path. A subprocess boundary does not establish
protection for browser, network or connected-app effects.

Then give the normal documentation to a fresh agent for an ordinary invocation
and a recoverable failure. Record what was actually exercised. Unit-test fixtures
do not establish that a native application or model interaction occurred.
A confusing interface is a tool defect, not automatically missing agent prose.

## Adoption and maintenance

AI-written automation is candidate software until reviewed and exercised. The
active task's author cannot change its certifier and immediately use that new
certifier as independent proof. Separate that change, preserve the old contract,
and require valid and violating controls. Keep secrets and unrelated user data
out of examples and receipts. A checksum establishes identity, not correctness.

Keep the operation only when its benefit justifies maintenance and context cost.
Removal in favor of a better native tool is a successful outcome.

## Example and near-miss

A startup operation can report the specific application revision, dependency
versions, authentication mode, owned process identity and observed readiness.
That does not establish persistence, permissions or an end-to-end user journey.
A latency check can use a repeatable workload but must retain environmental
conditions and observed variation rather than promise identical numbers.
