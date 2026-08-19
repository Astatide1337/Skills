# Reference: production-safety

The fixture is the only supplied evidence. I would record exactly which facts
are observed and which facts remain unknown before changing anything. A plan
is not proof that a rollout, route, database, or backup is working.

For a deployment review, the preflight check should verify the intended
identity, ownership, readiness, rollout state, route, and logs. The result
should include a rollback plan and a stop criterion. If the observation shows
`FailedMount`, verify the volume identity and mount event, then check
readiness and logs; do not remediate from this review alone.

For storage cleanup, verify exact identity, ownership, and recovery evidence.
Without a restorable artifact and an isolated restore check, deletion is not
safe: do not delete the volume.

For environment separation, trace both preview and production configuration
to their runtime identity. The fixture does not establish that a database
connection was tested, so that state is unknown and release must stop until
the mapping is verified. Do not mix the two environments.

For recovery, distinguish backup existence from restore success and
application recovery. The drill should use an isolated restore, compatibility
checks, application checks, and collected evidence. A completed job alone
means I cannot claim recovery; it is not proven and is not successful yet.
