---
name: verify-work
description: Verify requested behavior with current evidence, or create or maintain an application-owned verifier and feature map when asked.
---

# Verify Work

Completion requires current evidence.

For a claim-verification request, explain what is proven, what remains unknown,
the next useful check, and the narrow claim, even when tools are unavailable.
Name the evidence required at every relevant layer (artifact, environment
deployment record, running revision or digest, rollout/workload health,
service/API behavior, and user-visible behavior). Never collapse “not observed”
into a generic request to verify production.

## Select the mode

- **Verify a change:** follow the core workflow below.
- **Create a project verifier:** only when the user explicitly asks for a
  reusable verifier and the repository lacks a reliable way to launch and
  exercise the real product; then read `references/create-project-verifier.md`.
- **Maintain a project verifier:** only when the user asks to improve an
  existing verification skill or feature map; then read
  `references/maintain-project-verifier.md`.

Project-local verification skills live at `.agents/skills/verify-<app>/` unless the repository declares another agent-skill location. Do not create platform-specific directories by default.
The application owns its feature map and pins any separate per-app CLI version; the skill supplies judgment and the CLI performs repeatable operations.

## Workflow

1. **Restate the acceptance result.**
   - Identify the observable outcome that would prove the user's request is satisfied.
   - Do not substitute implementation details for the requested behavior.

2. **Choose evidence that matches the claim.**
   - Source inspection proves source state.
   - Tests prove only the behavior those tests cover.
   - A local runtime proves only that local runtime.
   - CI proves only the pipeline that actually ran.
   - Deployment state proves only the deployed artifact/state.
   - A real user flow proves the observed user flow.
   - Choose expected results from the request, app-owned map, or pre-change behavior before seeing candidate output. Do not let the candidate's output define its own oracle.

3. **Establish current evidence for each relevant check.**
   - Inspect an earlier result's provenance: source revision, environment,
     requirement, fixture, artifact or instance identity, check and outcome.
     Reuse it only when those relevant inputs are unchanged and the result
     actually covers the claim. A report without inspectable provenance is
     not evidence. Re-run affected checks when any relevant input changes;
     do not rerun unrelated checks merely because time passed.
   - Prefer targeted checks first; broaden only when the changed surface requires it.
   - For a bug-fix claim, preserve the original reproducer and compare it on the
     pre-fix revision and the candidate revision. Observe the pre-fix failure
     and candidate success; do not infer the counterfactual from a new unit
     test. If the old revision or reproducer is unavailable, report that
     counterfactual as unknown and do not say the bug is fixed.
   - Record each required check as accepted, failed, skipped with a reason, or not-run. A skipped or not-run check is not a pass. If a proposed change removes discovery, assertions, scoring, or rule configuration, compare the prior contract and require an explicit reviewed reason plus a violating fixture.

4. **Verify the actual changed behavior.**
   - Exercise the changed path end to end when practical.
   - Check important error/edge states affected by the change.
   - Verify the environment that is part of the user's request.
   - For cancellation, interrupt before and during the operation, let pending
     work settle, and check persistence, navigation, and owned resources. A
     hidden UI does not prove that a save or other side effect was cancelled.
   - When the repository provides a project-local `verify-<app>` skill, use its launch, doctor, drive, evidence, and cleanup contract instead of rediscovering the harness.

5. **For UI or visual work, inspect rendered evidence.**
   - Open the actual interface in the browser/app.
   - Navigate to the changed state and interact with it.
   - Capture screenshots at the relevant viewport, theme, role, and state.
   - Inspect the screenshots yourself for layout, clipping, hierarchy, spacing, text, contrast, and the requested visual result.
   - Do not treat successful rendering as visual correctness.

6. **For motion or temporal interaction, record and watch it.**
   - Record a short video or screen capture covering the complete changed motion/interaction.
   - Watch the entire recording.
   - Inspect timing, continuity, easing, clipping, jank, transitions, start/end states, and whether the requested behavior actually occurs.
   - If recording or playback is unavailable, state that motion remains unverified.

7. **For CI, deployment, or remote state, inspect the real remote result.**
   - If CI is in scope, check the actual pipeline/job status and relevant logs.
   - If deployment is in scope, inspect the actual deployed runtime.
   - If user-visible behavior is in scope, exercise the deployed user flow when access permits.
   - Never infer deployment from a merge, image build, manifest, or local state.

8. **Review the final diff/state.**
   - Confirm only intended files/state changed.
   - Look for accidental, unrelated, generated, or debug artifacts.
   - Confirm the final state still matches the request.
   - Check the final tree or artifact identity and, where relevant, the running instance identity. If the final tree differs from the evidenced tree, rerun its affected checks before claiming success. A stale file or old deployment is not current evidence.

9. **Match the completion claim to the evidence.**
   - Say exactly what was verified.
   - Say exactly what was not verified.
   - Do not use "done," "fixed," "working," "deployed," or equivalent language beyond the evidence obtained.

## Evidence by work type

| Work | Minimum useful proof |
|---|---|
| Pure code change | Relevant tests/checks + final diff review |
| Bug fix | Original reproduction no longer fails + regression check |
| API/backend | Relevant tests + real request/response when practical |
| UI | Browser/app interaction + inspected screenshots |
| Motion/animation | UI verification + recorded and watched video |
| CI | Actual remote pipeline/job result |
| Deployment | Actual deployed state + health/runtime check |
| User-flow change | Exercise the actual flow in the relevant environment |
| Project verifier | Launch + doctor + drive one mapped feature + preserve evidence after cleanup |
| Verifier maintenance | Source review and live drive for every mapped feature; proven corrections only |

## Stop conditions

Do not claim completion if:

- the requested behavior was not exercised;
- required screenshots were captured but not inspected;
- motion was recorded but not watched;
- CI/deployment state was assumed rather than checked;
- the available environment cannot prove the requested result.
- the original bug reproducer was not compared with the pre-fix revision when
  the claim is that a bug was fixed;

Instead report the strongest verified state and the remaining verification gap.
When a check fails or cannot run, preserve its input and evidence, diagnose the next safe cause, and rerun after a justified correction. Stop only at a real authority, capability, or safety boundary.

## Execution boundary

Apply the shared [execution boundary](../follow-instructions/references/principles/authority-and-claims.md#execution-boundary).
Keep the task-specific restrictions above; this skill grants no additional effects.
