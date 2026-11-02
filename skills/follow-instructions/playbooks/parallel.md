# Parallel modifier

## When

Use with the chosen workflow when independent work is useful, an authorized
delegation tool is available, and each worker can have clear ownership of files
or state.

Keep one accountable engineer for work that fits one session. For an explicitly
requested standing program that outlives one agent, use a coordinator that owns
briefs, dependencies and acceptance while PR owners write code. A sub-coordinator
is justified only when one track exceeds a single coordinator's useful capacity.
An ordinary feature does not need a hierarchy of coordinators.

## Inputs to establish

- primary route, dependencies, shared files/resources, writers/controllers,
  and the integration owner;
- each worker's outcome, input/source boundary, owned files, invariants,
  permitted effects, isolation, and return artifact;
- shared interfaces, budget, failure and cancellation handling, and the final
  integration check;
- original authority, acceptance, exclusions, remaining checks and evidence;
  the approved plan version only when the user or project requires one;
- role, difficulty, selected provider/model/reasoning, and the capability that
  supports the dispatch, per [agent selection](../references/agent-selection.md).

## Steps and decision points

1. For a new task pattern, complete and verify one representative unit end to
   end first. Establish its working contract and checks before considering
   concurrency for further units of the same pattern. This first unit tests
   whether the work can be split safely; it does not replace the full requested
   delivery or evaluation.
2. Settle shared contracts before splitting further units. Parallelism remains
   optional; split only independent work, and serialize competing state or
   unsettled interfaces.
3. Delegate no greater authority than the parent has. Isolate ports, data,
   credentials and browser sessions where relevant. Let workers use the
   selected domain skills and surface conflicts instead of overwriting peers.
   Include the requirements, owned files, permitted actions, outstanding checks
   and evidence in each task. Keep one integration owner; only that owner resolves
   a cross-worker plan change under the
   [approved-plan contract](../references/approved-plans.md).
   Preserve each requirement's condition and evidence: "migrate if deployed
   data exists" must not become an unconditional importer task. Superseding
   corrections update dependent worker briefs and checks before work resumes.
   For separately delivered branches, inspect their Git ancestry and intended
   PR base before delegation; disclose an intentional stacked dependency.
   Give each branch/PR one writer responsible through delivery. Pass upstream
   results and decisions to workers that depend on them; children do not inherit
   siblings' context. State standing constraints, forbidden actions and the
   evidence each worker must return.
4. Inspect returned diffs/artifacts and checks yourself. For delegated
   implementation with executable acceptance, run the reviewed checker through
   [parent acceptance](../../verify-work/references/independent-acceptance.md#parent-acceptance)
   on the current candidate. A worker's `completed` status only ends its run.
   Have the responsible
   owner resolve overlapping edits, integrate the changes, and exercise the
   affected end-to-end path. Verify the integrated result, including uncommitted
   and untracked files. Independent review covers the actual final artifact, not
   a worker's earlier green branch. Repair real in-scope defects; do not forward
   them as completed work.
5. Stop delegation when coordination costs exceed its benefit. If no tool is
   available, execute sequentially and report that parallelism was not used.
   For standing programs, use a bounded rolling window of independent owners,
   not a fixed swarm size or blocking batch. Inspect native completion events and
   current artifacts, integrate verified units as dependencies permit, and account
   for every child as completed, cancelled, failed or superseded. Merge remains
   separately authorized; a pilot can finish at verified PR readiness.

## Failure and recovery

On interruption, retain the last revision, ownership, remaining units and
evidence in the existing task record. Recheck state on resume. A worker's "done"
or green branch is not integration proof; retry, reassign, or serialize only
within the parent authority.

Use supported completion wakes and PR watches.
Follow returned continuation instructions; do not poll or message an idle worker
merely to check its status. Cancel a superseded run before replacement. A
delayed result must match the current unit ownership and source before
integration. A timeout alone does not establish cancellation. Reconstruct the
task from the retained contract and live state on resume, not a worker's summary
or transcript modification time.

After the same approach fails twice or work
yields no new evidence, use [self-reflect](../../self-reflect/SKILL.md) and the
existing checkpoint to hand the actual artifacts to one fresh debugging/review
agent for a discriminating next action when tools and authority permit. Present
the author's theory as a hypothesis. If delegation is unavailable, record that
limit; do not claim an independent review occurred.

## Completion evidence

Provide each returned artifact, integrated diff/revision, conflict decisions,
checks and actual user journey. Passing individual workers without the
integrated result is incomplete.

## Example

For a series of similar authorized features, the owner first completes and
verifies one feature end to end. If its interface and checks work, independent
remaining features may be delegated. The owner then verifies the integrated
journey and reviews each diff.

## Near-miss

Two workers editing the same migration or secret configuration are not safely
parallel; serialize ownership rather than creating a custom coordinator.
