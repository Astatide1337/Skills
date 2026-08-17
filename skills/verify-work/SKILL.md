---
name: verify-work
description: Use this skill before claiming that implementation, debugging, refactoring, UI work, CI work, deployment work, or any other engineering task is complete or correct. Verify the observable result the user actually asked for, not only that code compiles or tests pass. For visual or interactive work, inspect the real UI with screenshots; when motion, animation, scrolling, drag/drop, video, or other temporal behavior matters, record and watch the recording before claiming success.
---

# Verify Work

Completion requires current evidence.

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

3. **Run the relevant checks now.**
   - Do not rely on an earlier run, another agent's report, or an assumed green state.
   - Prefer targeted checks first; broaden only when the changed surface requires it.

4. **Verify the actual changed behavior.**
   - Exercise the changed path end to end when practical.
   - Check important error/edge states affected by the change.
   - Verify the environment that is part of the user's request.

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

## Stop conditions

Do not claim completion if:

- the requested behavior was not exercised;
- required screenshots were captured but not inspected;
- motion was recorded but not watched;
- CI/deployment state was assumed rather than checked;
- the available environment cannot prove the requested result.

Instead report the strongest verified state and the remaining verification gap.
