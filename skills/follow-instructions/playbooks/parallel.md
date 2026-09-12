# Parallel modifier

## When

Apply only to a valid primary route when independent work is useful, an
authorized delegation tool exists, and shared writers/interfaces can be
bounded. Parallelism is not a replacement process or mandatory committee.

## Inputs to establish

- primary route, dependencies, shared files/resources, writers/controllers,
  and the integration owner;
- each worker's outcome, input/source boundary, owned files, invariants,
  permitted effects, isolation, and return artifact;
- interface/data contract, finite budget, failure/cancellation and final
  integration check.

## Steps and decision points

1. Settle the shared contract first. Split only independent units; serialize
   work that competes for state or depends on an unsettled interface.
2. Delegate no greater authority than the parent has. Isolate ports, data,
   credentials and browser sessions where relevant. Let workers use the
   selected domain skills and surface conflicts instead of overwriting peers.
3. Inspect returned diffs/artifacts and checks yourself. Resolve overlap at
   its owner, integrate coherently, and exercise the affected end-to-end path.
4. Stop delegation when coordination costs exceed its benefit. If no tool is
   available, execute sequentially and report that parallelism was not used.

## Failure and recovery

On interruption, retain the last revision, ownership, remaining units and
 evidence in the existing task record. Recheck state on resume. A worker's
 “done” or green branch is not integration proof; retry, reassign, or serialize
 only within the parent authority.

## Completion evidence

Provide each returned artifact, integrated diff/revision, conflict decisions,
checks and actual user journey. Passing individual workers without the
integrated result is incomplete.

## Example

For an authorized feature, one worker adds backend behavior and another tests
the independent UI states after the API contract is fixed; the owner runs the
integrated journey and reviews both diffs.

## Near-miss

Two workers editing the same migration or secret configuration are not safely
parallel; serialize ownership rather than creating a custom coordinator.
