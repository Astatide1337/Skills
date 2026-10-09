# Linux, network, and container incident diagnosis

## Trigger

Use when an authorized Linux, Docker/Podman, or Kubernetes incident crosses
process, name-resolution, route, namespace, listener, proxy, firewall, or
protocol boundaries and the failing layer is not yet established. If the task
is text-only or offline, use the supplied evidence and write a read-only probe
plan; do not execute probes against a live system.

This procedure specializes `systematic-debugging`. For live changes, data,
credentials, or recovery, `production-safety` owns the authorization and
rollback gates.

## Procedure

1. **Pin the failing path.** Record the exact source and destination, request
   or protocol, expected and observed result, time window, host, interface,
   namespace, container/workload identity, and current context. In Kubernetes,
   capture the cluster context, namespace, pod UID, and workload revision. Do
   not infer that a shell's host namespace is the application's namespace.
2. **Build the path from the source inward.** Use only layers that exist in
   this system:

   ```text
   caller -> DNS/name mapping -> route -> host/namespace link -> listener
          -> TCP/TLS/HTTP or application protocol -> dependency
   ```

   Mark each edge with the exact observation source and scope. Compare a
   failing request with one allowed control from the same source and namespace
   where practical.
3. **Take the smallest read-only snapshot.** After confirming the target and
   permission, collect only the observations needed to separate the next two
   plausible layers. Typical Linux commands are `getent ahosts <name>`,
   `ip route get <resolved-ip>`, and `ss -lntp`. For an owned Docker target,
   use scoped `docker inspect` network fields and recent `docker logs`; avoid
   dumping full environment/config fields. For an authorized Kubernetes
   target, use `kubectl config current-context`, scoped `kubectl get` or
   `describe`, and bounded `kubectl logs`. Redact secrets and personal data in
   log output. Use `curl` only against an owned, documented, side-effect-free
   health/read endpoint, with a short timeout and a known destination.
4. **Choose a discriminating check.** Branch on evidence, not the user-facing
   error alone:
   - If the resolved address is wrong, compare the name source and resolver
     view before inspecting routes.
   - If resolution is correct but `ip route get` fails or selects an
     unexpected interface, compare routes in the failing namespace and one
     working namespace.
   - If the route reaches the destination network but `ss` shows no listener
     or only a loopback listener, inspect the service's effective bind address
     and namespace. A loopback-only listener blocks a client in a different
     network namespace that targets the container or Pod IP. A process sharing
     the destination namespace can still reach `127.0.0.1`; containers in one
     Kubernetes Pod share a network namespace. Confirm source and destination
     namespace and address before making this diagnosis. It does not prove that
     firewall rules are correct or that the captured state is still live.
   - If the TCP connection completes but TLS or HTTP fails, inspect the
     negotiated protocol, certificate name, proxy path, status, and response
     body before changing network rules.
   - If all shown layers work but the application request fails, trace the
     handler and dependency path; do not keep changing routes or firewall
     policy.
5. **Keep observations separate from remediation.** State which layer is
   supported, which alternatives the evidence rejects, and what remains
   unobserved. A local/synthetic capture is not current host state. Do not
   restart services or containers, build/pull images, prune resources, change
   routes/firewall/sysctls, alter network policy, run `kubectl exec`, or change
   credentials/security settings as a diagnostic shortcut. Those actions need
   separate authorization and the relevant `production-safety` recovery plan.
6. **Verify an authorized change at the same boundary.** If a change is
   explicitly authorized, capture pre-change state, make one scoped change,
   repeat the original failing request and the allowed control, check service
   health and relevant telemetry, and record rollback/recovery status. A
   successful command or one healthy endpoint does not prove the entire path.
7. **Report bounded evidence.** Include the target identity/context, exact
   probe and output, first supported failing layer, rejected hypotheses,
   remaining unknowns, action taken (or none), and the next safe observation.
   Separate static/configuration, local runtime, cluster, external service,
   and user-visible evidence.

## Executable example and negative control

Where read-only probing is authorized, substitute the observed service and
resolved address into this sequence; run each command in the namespace named
in the incident:

```bash
getent ahosts "$SERVICE"
ip route get "$RESOLVED_IP"
ss -lntp
```

For a supplied snapshot, run the local Linux/container contract case instead:

```bash
uv run --frozen python -m unittest \
  evals.tests.test_workflows.WorkflowContractTests.test_linux_container_diagnosis_separates_route_from_listener_scope -v
```

The case contains a peer request, a valid name resolution and route, a
matching container network address, a loopback-only service listener, and a
successful local health request. The acceptance control rejects a diagnosis
that blames DNS or routing, omits firewall/live-state/bridge-policy
uncertainty, or records or proposes an unauthorized restart or network
mutation, including when a suggestion is smuggled into an unknowns field. It
verifies a fixed synthetic artifact schema only; it does not inspect a live
host, container, or cluster.
