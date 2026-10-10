# Maintain a project verifier

Use this when asked to keep an existing application-owned verify-* skill and feature map aligned with source and live behavior. Edit only that verifier, its map, and its owned helpers; report product defects without changing product code or rewriting expectations to bless the defect.

1. **Locate and pin:** find the app's committed verifier, feature map, locked CLI version, and actual executable. Reject unsupported versions. Derive the clean app HEAD at launch and compare it with the run manifest; do not make the committed map self-reference its own commit. If no verifier exists, create one only when requested.
2. **Trace:** reconcile every mapped journey with its source entry point, types, selectors, data ownership, and expected user result. Preserve independent expectations; do not derive them from candidate output.
3. **Check structure:** compare the map's feature index and required assertions with the prior revision. A removed journey, assertion, scorer, discovery rule, or lint rule needs an explicit reviewed reason and a violating fixture proving the intended boundary still rejects bad behavior.
4. **Drive:** doctor the intended instance, then exercise each mapped journey at least once. Re-run doctor or reset after surprising behavior. Record accepted, failed, skipped, and not-run separately, with a reason for each skipped check.
5. **Recover:** fix proven verifier drift and re-drive. If a check fails, preserve its input and evidence, continue safe diagnosis, and do not mark it skipped or weaken the expected result to get green.
6. **Clean:** stop only run-owned processes and scratch state. Confirm evidence still exists after cleanup.

Report clean only with source and live coverage of every mapped journey, changed only for corrections re-driven successfully, or blocked with the exact unavailable capability and the safe checks completed. Do not open a branch, commit, push, or PR unless requested.
