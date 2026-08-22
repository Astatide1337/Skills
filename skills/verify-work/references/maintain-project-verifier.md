# Maintain a project verifier

Keep an existing repository-local verification skill and feature map aligned with both source and live behavior.

## Scope

Edit only the verifier's own `SKILL.md`, `features/`, and owned harness helpers. Do not change product code. Classify a mismatch as documentation drift, harness gap, unreachable prerequisite, or product defect.

## Maintenance pass

1. **Locate:** find the declared project-local `verify-*` skill. If several
   exist, resolve the target. If none exists, report that absence; create a new
   verifier only when the user explicitly asks for one.
2. **Index:** reconcile the feature index with its sibling files; remove dead or duplicate entries and add proven omissions.
3. **Source review:** trace every feature from its user entry point through source. Record cited drift and one live recipe per feature. Parallel read-only review is optional when the environment permits it.
4. **Reconcile:** spot-check suspected drift and combine recipes into the fewest safe app states. Require a concrete source path before declaring a feature missing.
5. **Live pass:** doctor the instance, then exercise every feature at least once. Re-run doctor or reset after surprising behavior. Keep captured evidence through every cleanup and remove failed-run residue promptly.
6. **Triage:** fix verifier documentation or harness gaps and re-drive them. Report product defects without editing the product or rewriting the map to bless the regression.
7. **Conclude:** report one outcome:
   - **clean:** every feature received source and live coverage; no correction needed;
   - **changed:** proven verifier corrections were made and re-driven;
   - **blocked:** state exactly which coverage or safe correction could not finish.

Keep run notes in scratch space rather than committing them. Do not open a branch, commit, push, or PR unless the user explicitly asks.
