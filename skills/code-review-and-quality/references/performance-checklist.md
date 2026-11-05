# Performance review checklist

Use this checklist for a suspected performance regression. For measured diagnosis, use the
[performance playbook](../../follow-instructions/playbooks/performance.md);
for controlled optimization, use [hillclimb](../../hillclimb/SKILL.md).

For each suspected regression, record the affected operation, workload, and
observable metric. Check:

- queries and API calls are bounded, paginated, and free of accidental N+1 work;
- loops, recursion, batching, and concurrency have explicit limits;
- hot paths avoid repeated parsing, allocation, serialization, and synchronous
  I/O where the runtime makes that material;
- query plans, connection pools, lock contention and external calls do not
  introduce a bottleneck at the affected workload;
- payload sizes, cache growth, CPU, memory and garbage collection remain bounded
  under representative load;
- UI changes preserve stable keys and avoid unnecessary re-renders or oversized
  client bundles;
- cache scope, key, freshness, invalidation, and privacy are explicit;
- lazy/deferred work has a before/after metric and does not delay required
  correctness or accessibility behavior;
- lockfile or dependency changes are checked for bundle/runtime impact.

If no measurement or reproducible workload is available, label the finding as a
hypothesis and state the smallest safe measurement needed. Never claim a
performance improvement from code shape alone.

Before changing a suspected bottleneck, profile or trace the actual path and
use the established workload, environment, sample count, noise tolerance and
threshold for keeping the change. Repeat the same measurement after the change and keep
it only when the threshold and correctness checks pass. Add a regression
benchmark, limit, test or monitor when practical.
