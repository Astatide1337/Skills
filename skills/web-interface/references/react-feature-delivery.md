# React feature delivery

## Trigger

Use for a user-visible change in an existing React or Next.js application when
behavior crosses more than one UI state, route, form submission, or shared
component boundary. Use the base workflow in `web-interface/SKILL.md` for
smaller visual edits. Read `component-authoring.md` when creating a reusable
primitive or component, `component-apis.md` when changing a shared component
contract, and `web-audit.md` for a review or final rendered audit.

## Procedure

1. **Set the observable outcome.** Name the affected route/component, user
goal, and the action that should complete it. Record current behavior and
preserve unrelated work. Derive expected results from the request and existing
product contract, not from a candidate implementation or its self-authored
test.
2. **Trace state ownership.** Follow the event from the control through local
or shared state, URL/router state, request/cache layer, and rendered result.
Keep shareable navigation state in the URL when existing product conventions
require it. Identify the owner for each transition and prevent stale async
responses from overwriting newer state.
3. **Map applicable states and transitions before editing.** For each changed
flow, write expected behavior for the states it can actually reach: initial,
loading/pending, empty, invalid input, server failure, success/populated,
long content, and disabled or selected states where applicable. Include the
keyboard/focus result and recovery action for each error state. Do not add
irrelevant states just to fill a checklist.
4. **Inspect the existing design and component contract.** Read the nearest
screen, established primitives, tokens, product copy, route patterns, and
focused tests. Reuse existing controls. For shared components, check native
semantics, accessible names/descriptions, keyboard operation, state ownership,
props/refs, and all current call sites before changing the public API.
5. **Implement the smallest coherent change.** Preserve the product's visual
language. Prefer native links, buttons, form controls, and landmarks; add ARIA
to complete semantics rather than imitate them. Keep one source of truth for
controlled state. Handle async completion, cancellation/unmount, duplicate
submission, and error recovery at the state owner. Preserve focus and typed
input through errors and hydration.
6. **Run focused deterministic checks.** Use the repository's existing test
and lint commands without installing dependencies. Add or update assertions
for each changed transition and an allowed control. Test a valid case and a
failure or invalid case. Do not let a component snapshot or source assertion
stand in for interaction behavior. If the project already has Playwright, a
focused browser test can use this shape, adapting selectors and expected copy
to the actual product:

   ```ts
   const email = page.getByLabel('Email address');
   await email.fill('not-an-email');
   await page.getByRole('button', { name: 'Save profile' }).click();
   await expect(email).toHaveAttribute('aria-invalid', 'true');
   await expect(page.getByText('Enter a valid email address')).toBeVisible();

   await email.fill('person@example.test');
   await page.getByRole('button', { name: 'Save profile' }).click();
   await expect(page.getByRole('status')).toContainText('Changes saved');
   ```

   Run the project's existing browser-test command for the focused spec, such
   as `pnpm exec playwright test path/to/profile.spec.ts --project=chromium`,
   only when that runner and project configuration already exist. Do not install
   or fetch a browser as part of an offline or restricted task.
7. **Inspect the rendered flow.** With an available authorized preview, open
   the changed route and exercise it with pointer and keyboard. Inspect the
   changed states at relevant desktop and narrow widths, supported themes, and
   actual long/empty/error content. Check focus visibility/order, labels and
   announcements, clipping/overflow, contrast, console errors, and hydration.
   Capture and inspect screenshots of the relevant states after corrections.
   Source, unit, and DOM tests do not establish rendered visual acceptance.
8. **Report by evidence layer.** Record the source revision, exact command, and
   inspectable test result. When a supplied packet lacks execution provenance,
   label its result as packet-reported rather than verified. Separate source
   and deterministic test results from browser interactions and inspected
   screenshots. State which states and widths were actually exercised, what
   failed or was skipped, and what remains unknown. If a preview, browser, or
   screenshot inspection was unavailable, mark rendered acceptance as pending;
   do not imply it was checked.

## Acceptance record

Keep a small state table for the changed path, with expected result, check run,
and outcome. Mark checks `passed`, `failed`, `skipped` with a reason, or
`not-run`. A complete UI acceptance claim needs a real interaction in the
relevant browser/app plus inspected screenshots; passing deterministic tests
alone supports only the tested logic and semantics.
