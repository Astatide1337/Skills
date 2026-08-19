# Untrusted integrations

## Webhooks and callbacks

- Authenticate the exact raw request bytes using the provider's documented
  signature scheme before parsing or performing side effects.
- Validate timestamp/freshness and bind the signature to the intended endpoint
  or account where supported. Store event identifiers for replay resistance.
- Make processing idempotent and transactionally claim work before side effects.
  Expect duplicates, delay, reordering, concurrency, and provider retries.
- Return bounded errors, rate-limit abuse, and retain correlation/audit metadata
  without logging credentials or full sensitive payloads.

## Server-side fetches and redirects

- Prefer fixed destinations. Otherwise allowlist scheme, host, port, and path;
  resolve and validate every address; block loopback, private, link-local,
  metadata, and other special-use ranges for both IPv4 and IPv6.
- Prevent DNS rebinding by binding validation to the actual connection or using
  an egress proxy. Revalidate redirects or disable them. Bound response size,
  decompression, content type, redirects, and timeouts.
- Apply network egress policy as a second layer; application URL parsing alone
  is not a complete SSRF defense.

## File and archive handling

- Generate server-side storage names; never join an untrusted filename to a
  writable or served path. Store outside executable/static roots.
- Bound upload, extracted, decoded, pixel, page, and processing sizes. Inspect
  content rather than trusting extension or declared MIME type.
- Treat archives, SVG, HTML, office documents, media parsers, and converters as
  hostile processing boundaries. Reject traversal, links, devices, and archive
  expansion outside the isolated destination.
- Authorize upload and download separately. Serve with deliberate content type,
  disposition, caching, and malware/quarantine policy.

## Third-party APIs and queues

- Treat provider responses and queue messages as untrusted. Authenticate the
  channel, validate schemas, and constrain downstream effects.
- Bound retries and use idempotency keys or deduplication around money, email,
  provisioning, and destructive actions. Preserve dead-letter/replay evidence.
