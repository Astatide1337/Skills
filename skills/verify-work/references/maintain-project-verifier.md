# Maintain a project verifier

Use this when asked to align an existing application-owned `verify-*` skill
and feature map with source and live behavior. Edit only that verifier, its
map and its helpers. Report product defects without changing product code or
rewriting expected results to accept the defect.

1. **Identify the verifier and runtime.** Find the committed skill, feature
   map, locked CLI version and actual executable. Reject unsupported versions.
   Derive a clean app HEAD at launch and compare it with the run manifest;
   do not make the committed map refer to its own commit. Create a missing
   verifier only when requested.
2. **Trace each mapped journey.** Compare the map with source entry points,
   types, selectors, data ownership and expected user results. Keep expected
   results independent of candidate output.
3. **Check for lost coverage.** Compare the feature index and required
   assertions with the prior revision. Removing a journey, assertion, scorer,
   discovery rule or lint rule needs an explicit reviewed reason and a test
   showing that the intended violation is still rejected.
4. **Exercise every mapped journey.** Run doctor on the intended instance,
   then each journey at least once. Rerun doctor or reset after surprising
   behavior. Record accepted, failed, skipped and not-run results separately;
   give a reason for every skipped check.
5. **Repair proven verifier errors.** Rerun each corrected path. For a failed
   check, preserve its inputs and evidence and continue safe diagnosis. Do not
   mark it skipped or weaken its expected result to pass.
6. **Clean up.** Stop only processes and temporary state owned by the run.
   Confirm the evidence remains available.

Report the verifier as clean only after source inspection and live execution
cover every mapped journey. Report a correction only after successfully
rerunning it. If blocked, name the unavailable capability and the safe checks
completed. Do not open a branch, commit, push or create a PR unless requested.
