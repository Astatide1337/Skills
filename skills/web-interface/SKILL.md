---
name: web-interface
description: Design, implement, prototype, optimize, or review user-facing web UI and components, including layout, accessibility, interaction, responsiveness, and visual QA. Not backend-only work.
---

# Web Interface

Build the rendered product, not an imagined screen. Keep changes coherent with
the existing application, accessible in real use, and verified in the states
they affect.

## Scope and mode

- Treat this as a web-interface task only. If the request has no user-facing
  surface, do not apply this skill.
- Match the requested mode. For a text-only plan or review, use only supplied
  artifacts and label missing visual evidence; do not imply that an app was
  run, a screenshot was captured, or a component was installed.
- Do not invent domain concepts, labels, metrics, routes, destinations, API
  contracts, or data merely to make an interface look complete.
- Do not turn a visual prototype into production code without the normal
  implementation and verification work.

## Choose the lane

Classify the task before changing code. Load every reference that matches the
actual work, but do not read the full library by default.

| Situation | Read |
| --- | --- |
| React or Next.js code has a user-visible performance concern | [React and Next performance](./references/react-next-performance.md) |
| A reusable component has prop bloat, shared state, or an API-design problem | [Component APIs](./references/component-apis.md) |
| Creating a reusable primitive, component, or design-system foundation | [Component authoring](./references/component-authoring.md) |
| Using or composing shadcn components in a project with `components.json` | [shadcn projects](./references/shadcn.md) |
| Running the shadcn CLI, adding/updating items, changing presets, or working with registries | [shadcn operations](./references/shadcn-operations.md) |
| Auditing UI code, accessibility, UX, or final interface quality | [Web interface audit](./references/web-audit.md) |
| The user explicitly wants competing visual directions | [UI prototyping](./references/ui-prototyping.md) |

Use the base workflow below for every lane. A React project does not
automatically make every UI change a performance refactor, and a Tailwind
project is not necessarily a shadcn project.

## Base workflow

1. **Bound the change.** Identify the affected screen, user goal, existing
   contract, and requested mode. Preserve unrelated user work.
2. **Inspect before designing.** Read the nearby UI, existing components,
   tokens, typography, spacing, navigation patterns, and real product copy.
   When implementation is authorized, open the current interface before
   proposing a new visual language.
3. **Reuse before creating.** Use established primitives, variants, semantic
   tokens, and component patterns. Create a new primitive only when the
   existing system cannot express the requested behavior cleanly.
4. **Implement the smallest coherent experience.** Keep hierarchy intentional,
   copy specific, and decoration subordinate to content or interaction. Avoid
   visual-system changes for a local request.
5. **Verify what changed.** Exercise the changed controls and inspect the
   rendered state. Repeat after correcting visible defects. If the interface
   cannot be opened, report that as an acceptance gap instead of guessing.
6. **Preserve accepted choices.** Treat explicit user corrections as constraints
   for the current task. Keep accepted parts stable while iterating elsewhere.

## Interface baseline

Apply the relevant checks; do not mechanically add patterns that do not fit
the surface.

- Prefer native semantic elements. Use a button for actions and a link for
  navigation; add ARIA only when native semantics do not cover the need.
- Give every interactive control an accessible name, visible focus treatment,
  keyboard operation, and a usable target. Preserve or return focus for
  overlays where appropriate.
- Give form fields real labels, appropriate input types and autocomplete,
  inline validation feedback, and a clear pending/error result. Do not block
  paste or rely on placeholders as labels.
- Design the actual states the change can enter: default, hover/focus/active,
  disabled, loading, empty, populated, validation error, server error, and
  short or long content where applicable.
- Preserve responsive behavior and supported themes. Check clipping, overflow,
  unexpected scroll, contrast, readable line length, and useful hierarchy at
  the affected breakpoints.
- Make motion purposeful, interruptible, and compatible with reduced-motion
  preferences. Do not use animation to conceal loading or layout problems.
- Keep UI state that must survive sharing, reload, or Back/Forward navigation
  in the URL when the product's conventions support it.
- Treat images, lists, and dynamic content as layout risks: reserve image
  dimensions, handle failure/empty content, and do not render unbounded lists
  without an appropriate rendering strategy.

## Visual verification

For implementation work with an available preview or browser:

1. Navigate to the changed screen and interact with the altered controls.
2. Capture and inspect screenshots for the relevant viewport, theme, and
   state combinations.
3. Check alignment, spacing, type, contrast, overflow, copy, neighboring
   consistency, and focus behavior from the rendered result.
4. When time-based behavior changes, record and inspect the complete
   interaction or animation; check timing, interruption, layout shift, jank,
   clipping, and start/end states.

Use the environment's attached preview or in-app browser. Do not substitute
source inspection for visual evidence, and do not claim visual acceptance if
the render cannot be inspected.

## Review output

For a review, group findings by file and use `file:line` when a line-addressed
artifact is available. Each finding must state severity, observed evidence,
and the smallest credible fix. Keep performance recommendations tied to a
measurable user-visible problem, not generic micro-optimization.

## Boundaries

- Use the project's supplied files and local configuration as the source of
  truth. This catalog does not authorize runtime documentation fetches,
  package installs, registry access, or credential use.
- Never claim a command, installation, screenshot, browser check, or file
  change occurred unless observed evidence supports it.
- Hand broad completion claims to `verify-work` when the task includes more
  than this interface change.
