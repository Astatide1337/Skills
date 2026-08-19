# Performance review checklist

Use this as a bounded review aid; use `performance-optimization` for measured
profiling and route/cache experiments.

For each suspected regression, record the affected operation, workload, and
observable metric. Check:

- queries and API calls are bounded, paginated, and free of accidental N+1 work;
- loops, recursion, batching, and concurrency have explicit limits;
- hot paths avoid repeated parsing, allocation, serialization, and synchronous
  I/O where the runtime makes that material;
- UI changes preserve stable keys and avoid avoidable re-renders or oversized
  client bundles;
- cache scope, key, freshness, invalidation, and privacy are explicit;
- lazy/deferred work has a before/after metric and does not delay required
  correctness or accessibility behavior;
- lockfile or dependency changes are checked for bundle/runtime impact.

If no measurement or reproducible workload is available, label the finding as a
hypothesis and state the smallest safe measurement needed. Never claim a
performance improvement from code shape alone.
