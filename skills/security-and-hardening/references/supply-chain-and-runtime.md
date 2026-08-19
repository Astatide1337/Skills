# Supply chain and runtime

## Dependencies and build inputs

- Resolve the real workspace and authoritative package manager/lockfile from
  repository and CI evidence. Use frozen or immutable installs.
- Review new direct and transitive dependencies, registries, names, maintainers,
  release history, source, licenses, lifecycle/build scripts, and lockfile diff.
- Treat install scripts, plugins, generators, build hooks, containers, actions,
  and third-party CI templates as executable code. Do not run them merely to
  decide whether they are trustworthy.
- Triage advisories by affected version, reachability, environment, exploit
  preconditions, impact, and available remediation. A clean advisory scan does
  not establish provenance or absence of unknown vulnerabilities.
- Prefer reproducible builds and verify artifact identity, signatures or
  attestations, provenance, and digest through deployment where supported.

## GitHub and GitLab delivery

- Minimize default job permissions and scope secrets to protected jobs and
  environments. Treat pull-request/fork content as attacker-controlled.
- Prefer short-lived OIDC/workload identity over stored cloud keys; constrain
  issuer, audience, repository/project identity, ref, environment, and job claims.
- Pin external automation to an immutable revision when feasible and review
  updates. Protect deployment environments and separate build from deploy authority.
- Never expose secrets to untrusted build steps, artifacts, caches, logs, or
  privileged runners. Verify which commit produced the deployed artifact.

## Images and containers

- Use reviewed minimal bases pinned by digest, rebuild for security updates, and
  remove compilers/package managers when they are not runtime requirements.
- Run as a non-root user where feasible; drop capabilities; avoid privileged
  mode, host namespaces, Docker sockets, writable host mounts, and broad devices.
- Make the filesystem read-only when supported, isolate writable paths, set
  resource limits, and constrain ingress/egress. Never bake secrets into image
  layers, build arguments, or build logs.
- Scan configuration, dependencies, and images, then triage findings rather than
  equating scan success with security.

## Kubernetes and OpenShift

- Apply least-privilege RBAC and remember that permission to create workloads
  can indirectly expose namespace secrets and node/service-account privileges.
- Use Pod Security Standards or equivalent admission policy appropriate to the
  workload; set security contexts, seccomp, capabilities, service-account token
  mounting, resources, and network policy deliberately.
- Keep confidential values out of ConfigMaps. Protect Secrets with encryption at
  rest, scoped access, short-lived identity, and controlled injection/rotation.
- Review image identity, admission policy, external exposure, operator/controller
  permissions, and the actual deployed manifest—not only source templates.
