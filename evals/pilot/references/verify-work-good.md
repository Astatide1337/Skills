# Reference: verify-work

The supplied merge, CI, image, and repository artifacts establish source and
build evidence. They do not establish cluster state, rollout state, pod
readiness, endpoint behavior, route behavior, logs, replicas, restarts, or
user-visible behavior. Those facts remain unknown, so I cannot claim the
deployment or feature is complete from the artifacts alone.

The verification sequence is: identify the image and artifact, inspect the
cluster rollout and pod status, check replicas and readiness, inspect
restarts and errors, verify endpoint routing and the route, and review logs. Record
the user-visible result separately. A zero exit code is only command
evidence; it does not prove deployment behavior.

For backup evidence, distinguish the backup artifact from a restore and from
application recovery. Verify artifact integrity, perform a restore in an
isolated environment, check schema compatibility, exercise the application,
and retain evidence for each step. The scheduler status does not prove
recoverability.

For a security fix, verify the deployed artifact, the protected runtime
behavior, and regression behavior. The merge and tests alone leave runtime
behavior still unknown; the fix is not proven until those checks are observed.
