# React and Next Performance

Read this only for a user-visible performance problem in a React or Next.js
surface. Treat each optimization as a hypothesis with a named metric and a
comparable baseline; report an expected benefit as unverified when measurement
is unavailable.

## Prioritize by impact

1. **Remove real request waterfalls.** Start independent work together and
   await only at the branch that consumes it. Keep true dependencies ordered;
   do not use parallelism to hide a dependency.
2. **Reduce initial work.** Avoid broad or barrel imports on hot paths,
   defer non-critical code and third parties, and load feature-specific code
   only when the feature is needed.
3. **Keep the server/client boundary narrow.** Fetch close to the server
   consumer, deduplicate equivalent work, and pass only the client data that
   the interaction needs. Do not expose server-only values or serialize large
   unused objects.
4. **Fix proven render costs.** Profile expensive renders before adding memo,
   transitions, deferred values, or caching. Move interaction-only work into
   the event path; do not subscribe a component to data used only by a callback.
5. **Treat caches as security and correctness decisions.** Define key,
   ownership/tenant boundary, freshness, invalidation, and eviction before
   sharing data across requests. Never cache authenticated data under an
   under-specified key.

## Safeguards

- Read the project's React and Next versions before using version-specific APIs.
- Preserve loading, error, cancellation, consent, analytics delivery, and
  accessibility behavior after changing scheduling or lazy loading.
- Prefer a small measured change over speculative JavaScript micro-optimizing.
