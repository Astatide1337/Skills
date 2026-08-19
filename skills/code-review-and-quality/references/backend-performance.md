# Backend performance

Optimize only from a reproducible measurement.

Record the metric, workload, environment, sample count, noise tolerance, and keep/revert threshold. Profile or trace the slow path before editing it. Check likely boundaries: query count and plans, pagination and result limits, cache bounds and invalidation, serialization and payload size, synchronous work, connection pools, lock contention, external calls, CPU, memory, and garbage collection.

Change one bottleneck at a time. Repeat the same measurement under the same conditions. Keep the change only when the result clears the predeclared threshold and correctness checks still pass. Add a regression benchmark, limit, test, or monitor when practical.
