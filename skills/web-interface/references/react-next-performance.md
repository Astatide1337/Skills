# React and Next Performance

Read this only for a user-visible performance problem in a React or Next.js
surface. Treat every optimization as a hypothesis with a named metric and a
comparable baseline. Mark expected benefits as unverified when measurement is
unavailable.

## Contents

- [Order of work](#order-of-work)
- [Eliminate waterfalls](#eliminate-waterfalls)
- [Reduce shipped code](#reduce-shipped-code)
- [Protect server performance](#protect-server-performance)
- [Control client work](#control-client-work)
- [Reduce proven render cost](#reduce-proven-render-cost)
- [Improve rendering and browser work](#improve-rendering-and-browser-work)
- [Apply JavaScript micro-optimizations last](#apply-javascript-micro-optimizations-last)
- [Use advanced and version-specific APIs carefully](#use-advanced-and-version-specific-apis-carefully)
- [Verify the result](#verify-the-result)

## Order of work

Prioritize by probable user impact:

1. Remove network or server waterfalls.
2. Reduce initial JavaScript, CSS, fonts, and third-party work.
3. Improve server concurrency, data boundaries, and cache behavior.
4. Fix client request duplication and global subscription waste.
5. Profile and reduce expensive React renders.
6. Improve long-list, DOM, and browser rendering behavior.
7. Apply JavaScript loop or allocation optimizations only on measured hot paths.

Do not turn ordinary React implementation into a blanket performance rewrite.
Name the symptom first: slow navigation, poor LCP or INP, excess transferred
bytes, server latency, hydration delay, or a measured render hotspot.

## Eliminate waterfalls

- Check cheap synchronous exit conditions before starting remote work.
- Start independent promises together and await them at the latest safe point.
- Represent partial dependencies as a graph: start downstream work as soon as
  its inputs exist instead of waiting for unrelated siblings.
- In route handlers and server actions, initiate independent I/O before
  authentication-independent computation, then await in dependency order.
- Split slow regions behind Suspense only when streaming improves useful paint;
  preserve error boundaries and avoid many tiny loading flashes.
- Keep true dependencies sequential. Parallelism must not obscure required
  ordering or start unauthorized work before access checks.

```ts
const userPromise = getUser(id)
const flagsPromise = getFlags()

const [user, flags] = await Promise.all([userPromise, flagsPromise])
```

Avoid creating a promise early when the user may not be authorized to perform
the operation or when the request has side effects.

## Reduce shipped code

- Import from analyzable leaf paths on bundle-sensitive paths. Inspect the
  package's export map before bypassing its public entrypoint.
- Avoid barrels that pull broad modules into a client bundle or server trace.
- Dynamically import heavy, feature-specific UI when the feature is not needed
  for the initial interaction.
- Load optional editors, charts, maps, and rich previewers only after intent or
  activation. Provide a stable loading state and reserve layout space.
- Defer analytics, chat widgets, logging, and other non-critical third parties
  until after the critical experience. Preserve consent and delivery semantics.
- Preload on strong intent, such as hover or focus, only when hit rate justifies
  the extra network work.
- Keep dynamic import paths statically analyzable; avoid constructing module
  paths from arbitrary runtime strings.
- Validate with a bundle report or transferred-resource comparison. A source
  import that looks narrower is not proof that the output is smaller.

## Protect server performance

- Authenticate server actions and route mutations like public API endpoints.
  Validate authorization near the data operation, not only in the UI.
- Deduplicate equivalent reads within a request when the framework supports it.
  Keep per-request memoization separate from cross-request caching.
- For a shared cache, define its key, tenant/user boundary, freshness,
  invalidation, maximum size, and eviction policy before use.
- Never place authenticated data in a cache keyed only by a public resource ID
  when the result varies by viewer, tenant, locale, or permission.
- Pass the smallest client-safe payload across the server/client boundary.
  Avoid serializing whole ORM records or duplicate objects into several props.
- Structure sibling and nested server components so independent reads overlap.
- Hoist immutable static I/O only when it is truly process-safe. Do not hoist
  mutable request state, headers, cookies, or user-scoped data.
- Use background or post-response hooks only for work that may safely occur
  after the response. Confirm framework version and delivery guarantees.
- Bound nested per-item concurrency; replacing a waterfall with an unbounded
  request fan-out can make the system slower or less reliable.

## Control client work

- Use the project's established data library to deduplicate identical client
  reads and coordinate revalidation. Do not add a library for a single request.
- Install a global event listener once when many components need it; remove it
  reliably and keep the handler identity stable.
- Mark scroll, touch, and wheel listeners passive only when they never call
  `preventDefault`.
- Version local-storage data, store only necessary fields, handle parse/schema
  failure, and avoid repeated synchronous reads during render.
- Keep browser-only storage reads hydration-safe and avoid a visible server to
  client content flash.

## Reduce proven render cost

- Do not subscribe a component to state that is read only inside a callback;
  read it at the event boundary when the state system supports that safely.
- Derive values during render rather than copying them into state with effects.
- Subscribe to a stable derived value when the raw source changes more often
  than the UI meaningfully changes.
- Use functional state updates when the next state depends on the previous one.
- Pass an initializer function to `useState` for expensive initial computation.
- Keep effect dependencies primitive or stable when that reflects the actual
  dependency. Never omit a dependency to silence tooling.
- Move interaction-specific work into the event handler instead of an effect
  that watches a flag set by the event.
- Do not define component types inside another component's render path.
- Split hooks whose independent concerns force unrelated updates together.
- Use `memo` only around a measured expensive subtree with stable props.
- Hoist stable non-primitive defaults so memoized children do not receive a new
  array, object, or function on every render.
- Do not wrap trivial primitive expressions in `useMemo`.
- Use transitions or deferred values for non-urgent expensive updates; keep the
  authoritative input state immediate and accessible.
- Store rapidly changing values in refs only when updates must not affect the
  rendered output.

Profile before and after. A lower render count is not automatically faster if
comparison, memoization, or cache maintenance costs more than rendering.

## Improve rendering and browser work

- Use `content-visibility` or virtualization for genuinely long content. Keep
  search, selection, accessibility, and scroll restoration behavior intact.
- Keep conditional rendering explicit when `0`, `NaN`, or an empty string could
  leak into output; prefer a ternary when the false case matters.
- Hoist static JSX only when it is independent of theme, locale, request data,
  and rendering environment.
- Animate a wrapper around complex SVG content when direct SVG animation causes
  browser inconsistencies.
- Reduce excessive SVG coordinate precision only after checking visual fidelity.
- Prevent hydration flicker by making server and client output agree or by using
  a deliberate pre-hydration strategy. Do not hide real mismatches with
  `suppressHydrationWarning`.
- Use loading transitions from the actual mutation/navigation state rather than
  maintaining a second boolean that can become stale.
- Add resource hints only for known, high-value origins or assets. Too many
  preloads compete with critical work.
- Use `async` or `defer` intentionally for scripts; preserve execution order
  where scripts depend on one another.

## Apply JavaScript micro-optimizations last

On a measured hot path, consider:

- Combine repeated passes over a large collection when it materially reduces work.
- Build a `Map` or `Set` for repeated lookups rather than scanning each time.
- Exit early before expensive comparison or transformation.
- Check collection length before deeper equality work.
- Use a single loop for min/max instead of sorting the entire collection.
- Hoist regular expressions and stable allocations out of hot loops.
- Cache repeated property or storage reads only when the source cannot change
  unexpectedly within the operation.
- Batch DOM reads, then DOM writes; avoid alternating measurement and mutation.
- Prefer immutable sorting with `toSorted` when supported, or copy before sort.
- Use `flatMap` when it clearly expresses a combined map/filter operation.
- Schedule non-critical work during idle time only with a timeout/fallback and
  without delaying required analytics, accessibility, or persistence.
- Bound function-result caches and include all correctness dimensions in keys.

Keep the clearer implementation when measurement does not show a worthwhile gain.

## Use advanced and version-specific APIs carefully

- Read installed React and Next versions before using `Activity`, `after`,
  `useEffectEvent`, resource-hint APIs, or changed ref/context behavior.
- Keep the latest event handler in a ref only when stable subscription identity
  is necessary; update the ref consistently and avoid hiding dependencies.
- Run one-time initialization at an application boundary, not through a fragile
  component effect that may execute more than expected in development.
- Do not blindly remove `forwardRef`, replace `useContext`, or adopt a new API
  because an upstream example targets a newer React release.

## Verify the result

1. Record the baseline metric, route, device/network conditions, and data shape.
2. Make one coherent change or a clearly attributable group of changes.
3. Repeat the same measurement and compare distributions, not one lucky run.
4. Exercise loading, empty, error, cancellation, consent, and accessibility states.
5. Check bundle and server changes in production-mode output when possible.
6. Report what was measured, what improved or regressed, and what remains a
   hypothesis.
