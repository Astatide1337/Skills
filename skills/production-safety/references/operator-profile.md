# Operator profile

These defaults reflect the catalog owner's recurring working patterns. They
personalize the workflow without replacing target-specific discovery.

## Authorization and working mode

- Treat `review-only`, `read-only`, `do not edit`, `do not deploy`, `do not
  commit`, and `do not push` as hard boundaries, even when write access exists.
- Keep diagnosis separate from implementation. A request to inspect or explain
  does not authorize a fix.
- For a requested change, commit, push, or deployment, perform only that stage
  and its normal verification; do not silently advance to the next stage.

## VPS and container-hosted services

- Resolve the exact host, deployment directory, repository revision, container
  runtime, Compose project/files/profiles, service names, image tags and digests,
  ports, reverse proxy, public hostname, TLS path, firewall, persistent volumes,
  environment-file names, and process supervisor before changing anything.
- Do not print entire environment files or secret stores. Retrieve only the
  minimum named value or metadata needed, and keep secret values out of reports.
- Treat volumes and bind mounts as persistent data. Commands such as `down -v`,
  image pruning, orphan removal, or project-name changes can be destructive.
- Clean up test containers, records, networks, and temporary credentials created
  by the verification, but prove ownership before removal. Never generalize a
  requested cleanup into deleting shared state.
- Verify both the internal service path and the public reverse-proxy/DNS/TLS path
  when the task claims the deployed stack works.

## GitHub, GitLab, and deployment provenance

- Map repository, remote, source branch, commit SHA, pipeline/workflow, artifact
  or image digest, target environment, deployment job, and currently running
  revision. A pushed commit is not proof that production runs it.
- Inspect required/manual jobs, environment protections, failed or skipped jobs,
  and rollback artifacts before deployment.
- Preserve user-authored or coworker changes. In review-only work, do not switch,
  merge, amend, commit, or push branches.

## Application and database verification

- The recurring stack includes document and relational databases; discover the
  actual engine and authoritative environment instead of assuming MongoDB,
  PostgreSQL, or a managed branch is in use.
- For migrations, check version compatibility, idempotency, indexes, backfills,
  mixed-version operation, record counts, rollback limits, and whether startup
  automatically runs migrations.
- For full-stack verification, define fixtures and cleanup before testing. Use
  isolated test identities/data where possible, capture created object IDs, and
  remove only those objects afterward.
- Report proof by layer: build/static checks, local stack, live API, deployed
  dependencies, and browser-visible flow. A mocked test or successful health
  endpoint does not establish an end-to-end user journey.

## Network-provider surfaces

- DNS, proxy, tunnel, and certificate dashboards remain safety-sensitive, but no
  specific provider is assumed. If the request authorizes navigation only, do
  not edit DNS, deploy, modify tunnels, or rotate certificates.
