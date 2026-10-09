# SRE incident operations

**Trigger:** A service is degraded, unavailable, over its latency or error
objective, or may have regressed during a rollout. Use this procedure when the
failure could involve a release, dependency, traffic shift, or service health.

**Objective:** Produce a current, evidence-bound incident assessment and the
next safe observation. A passing build or health probe alone is not proof of
user-visible recovery.

## Authority and inputs

Start in read-only mode. Identify the exact service, environment, region or
cluster, incident window, affected request path, and requested inspection
scope. Record whether the user authorized diagnosis only or a specific
operational change. Use the runtime source of truth for what is serving and the
deployment source of truth for what should be serving; do not treat desired
state as observed state. If live tools are unavailable, work from the supplied
snapshot, label runtime facts unknown, and name the read-only observation an
authorized operator would need. Do not run probes in an unapproved environment.

## Workflow

1. **Bound the symptom.** Record when the issue began, affected users or
   requests, error and latency changes, and a same-duration pre-incident
   baseline. Keep reported impact separate from measured impact.

2. **Establish the serving state.** Read the current rollout or process state,
   service identity, revision or image digest, traffic share, and recent
   deployment events. Compare the actual serving revision with the intended
   revision. For multiple replicas, zones, or canary cohorts, retain the
   per-cohort values instead of averaging away a partial failure.

3. **Compare a healthy control.** Compare the failing cohort with an unaffected
   cohort for the same service, region, and time window. Check user-path
   requests, errors, latency, saturation, and readiness/liveness separately.
   A ready process can still return failing requests. If both cohorts show the
   same symptom, do not attribute it to the newer revision on timing alone.

4. **Check dependencies with scoped evidence.** For each material dependency,
   record the observed state, source, time, scope, and request path covered. A
   missing, stale, access-denied, or out-of-scope signal remains unknown; it
   does not mean healthy or failed. If dependency state could distinguish the
   leading hypotheses, run one authorized read-only check for the same incident
   window and affected cohort.

5. **Choose the smallest discriminating observation.** State two or more
   plausible causes when evidence permits. Name the first read-only check, the
   observation expected under each cause, and what result would reject the
   current explanation. For a rollout-correlated symptom, bind a sample of
   failing requests to their serving revision and compare it with the
   unaffected revision. If request-level evidence is unavailable or the
   unaffected cohort also fails, downgrade the revision hypothesis and inspect
   shared traffic or dependencies.

6. **Set the action boundary.** Before any operational change, record the
   affected service and cohort, blast radius, active writers or controllers,
   exact proposed change, stop threshold, and recovery evidence. For a
   rollback, verify the target revision and artifact digest, deployment method,
   data or schema compatibility, and a tested recovery path. Do not restart,
   roll back, redeploy, scale, or reconfigure unless the user authorized that
   exact action and the production-safety gates are satisfied. If recovery
   state is incomplete, continue with read-only checks and report the missing
   fact.

7. **Verify an authorized change.** Capture the pre-change state, make one
   scoped change, and immediately check that the intended revision or setting
   is serving. Then verify the affected user path, error and latency signals,
   readiness, dependencies, and alerts over a stated observation window.
   If the stop threshold is crossed, execute only a previously authorized
   rollback path; otherwise stop and request direction. A successful command
   exit is not recovery evidence.

8. **Report the result.** Separate observed facts, assumptions, unknowns,
   hypothesis status, action taken (or none), and next safe check. Name the
   tested service, environment, revision, time window, and evidence sources.
   State whether evidence is a supplied snapshot, local runtime, CI result, or
   deployed user-path observation; do not claim a stronger layer.

## Deterministic acceptance

Run the synthetic incident contract and its controls:

```bash
uv run --frozen python -m unittest \
  evals.tests.test_sre_incident_operations -v
```

The packet contrasts a degraded canary with a healthy same-window revision,
keeps green readiness separate from user-path success, preserves unknown
dependency health, and rejects attribution when both revisions fail similarly.
It also withholds a rollback-safety claim when the artifact digest is missing
and the last healthy observation is stale. These checks verify the procedure
and fixture contract only; they do not measure agent behavior or establish
live service health.
