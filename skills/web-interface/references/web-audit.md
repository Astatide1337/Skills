# Web Interface Audit

Read this when reviewing UI code, accessibility, UX, visual quality, or the
final rendered result. Apply only checks relevant to the affected surface. This
is an offline, paraphrased audit rubric; if the user explicitly asks for the
latest upstream rules, verify them separately before claiming current coverage.

## Contents

- [Collect evidence](#collect-evidence)
- [Assign severity](#assign-severity)
- [Accessibility and focus](#accessibility-and-focus)
- [Forms](#forms)
- [Navigation and state](#navigation-and-state)
- [Touch, layout, and responsive behavior](#touch-layout-and-responsive-behavior)
- [Animation and temporal behavior](#animation-and-temporal-behavior)
- [Content, typography, and internationalization](#content-typography-and-internationalization)
- [Images and performance](#images-and-performance)
- [Theme, visual design, and browser behavior](#theme-visual-design-and-browser-behavior)
- [React and hydration safety](#react-and-hydration-safety)
- [Report findings](#report-findings)

## Collect evidence

For a code-only review, read the named files and their relevant component,
style, token, and test dependencies. Do not claim rendered or assistive-
technology behavior was verified from source alone.

For implementation acceptance:

1. Open the affected page in the attached preview/browser.
2. Exercise the altered controls with pointer and keyboard.
3. Inspect the relevant mobile and desktop widths, supported themes, and
   meaningful data/state combinations.
4. Capture and inspect screenshots; record and watch temporal behavior.
5. Check console/runtime errors and obvious network or hydration failures.
6. Repeat after corrections.

## Assign severity

- **Critical:** blocks a primary task for a broad group, causes likely data
  loss, bypasses a required confirmation, or makes the experience unusable.
- **High:** keyboard/screen-reader access is broken, focus is lost/trapped,
  content is unreadable, or a common state fails.
- **Medium:** meaningful responsive, error, performance, or clarity defect with
  a viable workaround.
- **Low:** polish or consistency issue with limited functional impact.

Do not inflate severity for stylistic preference. State the observed evidence
and the smallest credible fix.

## Accessibility and focus

- Use native semantics before ARIA. Actions are buttons; navigation uses links.
- Give icon-only controls and non-text affordances an accurate accessible name.
- Associate every form control with a real label or equivalent accessible name.
- Hide decorative icons/media from the accessibility tree; give meaningful
  images useful alt text and decorative images empty alt text.
- Keep headings hierarchical and include a skip path to primary content where
  repeated navigation warrants it.
- Make every flow keyboard-operable. Custom composites must implement the
  complete expected arrow-key, activation, dismissal, and Tab behavior.
- Show a visible, unobscured focus indication. Never remove outline without a
  replacement; use group focus treatment for compound controls.
- Trap focus only in modal interactions and restore it to a sensible invoker.
- Keep sticky headers, footers, banners, and overlays from covering focus.
- Announce async status, validation, and completion with a suitable polite live
  region without duplicating spoken content.
- Do not rely on color alone for status, selection, or error meaning.
- Preserve zoom and text resizing. Do not ship viewport settings that prevent
  users from zooming.
- Supply captions/transcripts/descriptions for meaningful media as applicable;
  keep media controls keyboard-accessible.
- Give small visual controls an adequate hit area; target roughly 44 CSS pixels
  on touch surfaces when layout permits.

## Forms

- Make labels clickable and avoid placeholders as the only label.
- Set meaningful `name`, `autocomplete`, input `type`, and `inputmode` values.
- Allow paste, password managers, one-time-code entry, and common input-method
  behaviors. Never block typing silently merely because input is invalid.
- Disable spellcheck for identifiers such as emails, codes, and usernames when
  corrections would be harmful.
- Let submission reveal validation instead of pre-disabling the button for
  incomplete input. Once a request begins, prevent duplicate submission and
  show an in-context pending state that retains the action label.
- Keep checkbox/radio label and control in one usable hit target.
- Place errors next to the affected fields, connect descriptions semantically,
  and focus the first invalid field after failed submission.
- Give errors a recovery step rather than only stating failure.
- Use Enter to submit ordinary single-line forms; use the product convention
  for multiline submit shortcuts without breaking newline entry.
- Warn before navigation when the user would lose meaningful unsaved work.
- Avoid reserved auth-like field names/autocomplete tokens for unrelated search
  or filter fields when they trigger password managers.
- Trim or normalize only at a clear boundary; do not mutate input while the user
  is composing text.

## Navigation and state

- Use links for destinations so open-in-new-tab, copying, and browser navigation
  continue to work.
- Put shareable or navigation-significant state—filters, tabs, pagination,
  expanded panels—in the URL when consistent with the product architecture.
- Preserve Back/Forward behavior and meaningful scroll restoration.
- Make routes and state deep-linkable; reloading a copied URL should reconstruct
  the same useful view when feasible.
- Confirm destructive actions or provide a clear, reliable undo window.
- Use optimistic updates only when success is likely and rollback/recovery is
  explicit.
- Ensure every empty/error screen offers a relevant next step instead of a dead
  end.

## Touch, layout, and responsive behavior

- Provide a tap/click and keyboard alternative for gestures unless the gesture
  itself is the essential task.
- Use touch behavior intentionally on controls and contain overscroll where
  drawers, sheets, or modals would otherwise scroll the background.
- During drag, suppress accidental selection and interaction without removing
  the alternate accessible operation.
- Avoid dead zones: every region that visually appears interactive should
  respond consistently.
- Autofocus only when a single primary desktop input clearly benefits; avoid
  opening the mobile keyboard unexpectedly.
- Prefer intrinsic CSS, flex, and grid layout over JavaScript measurement.
- Handle safe-area insets for full-bleed fixed surfaces.
- Test mobile, ordinary laptop/desktop, and wide layouts. Check both narrow and
  unusually long content at each meaningful breakpoint.
- Diagnose overflow rather than masking it globally. Check with persistent
  scrollbars so platform differences are visible.
- Keep text containers resilient with wrapping, clamping, or truncation and
  apply `min-width: 0` to shrinking flex children when necessary.

## Animation and temporal behavior

- Honor reduced-motion preferences with a reduced or absent alternative.
- Animate only when it clarifies state/cause or adds deliberate, restrained
  character.
- Prefer CSS, then the Web Animations API, before main-thread library animation
  when they can express the behavior clearly.
- Prefer compositor-friendly opacity/transform changes; avoid layout-triggering
  properties in frequent animation.
- List transition properties explicitly instead of transitioning everything.
- Choose transform origin and easing to match the object's movement and scale.
- Keep animations interruptible and responsive to new input.
- Give long, concurrent autoplay motion a pause/stop/hide mechanism; stop
  decorative loops under reduced motion.
- Apply SVG transforms to a suitable group/wrapper when direct element
  transforms behave inconsistently.
- Watch the entire recording for timing, start/end state, jank, layout shift,
  clipping, flashes, and accidental double animation.

## Content, typography, and internationalization

- Use specific active labels that describe the action; avoid generic “Continue”
  when the actual action can be named.
- Keep terminology consistent with the real product domain. Do not invent
  metrics or feature language to fill space.
- Design empty, sparse, typical, dense, loading, and error content.
- Handle very short and very long user-generated strings without breaking the
  layout.
- Keep headings readable and avoid awkward isolated words when supported by the
  type/layout system.
- Use the single ellipsis character for loading and actions that open a further
  prompt. Keep status wording consistent.
- Use tabular numerals for columns or displays where numeric comparison matters.
- Keep units, shortcuts, and tightly bound names together when a line break
  would harm comprehension.
- Format dates, time, numbers, and currency with locale-aware APIs.
- Infer language from user/browser language settings, not location.
- Mark brand names, code tokens, and identifiers as non-translatable when
  machine translation would corrupt them.
- Keep page titles accurate to the current view and state.

## Images and performance

- Give images intrinsic dimensions or an equivalent reserved aspect ratio to
  prevent layout shift.
- Load critical above-fold imagery intentionally and lazy-load below-fold
  imagery; do not mark every image high priority.
- Provide useful failure/fallback behavior for meaningful images and avatars.
- Prefer compressed video to large animated GIFs for loops, with a still and
  reduced-motion alternative.
- Virtualize or use an appropriate browser rendering strategy for genuinely
  large lists while preserving keyboard, search, and accessibility behavior.
- Avoid layout measurement during render and batch DOM reads separately from
  writes.
- Keep controlled input work cheap enough for each keystroke.
- Preconnect or preload only known critical origins/assets; excess hints compete
  with the resources they were meant to help.
- Load fonts with an appropriate display strategy, subset unused scripts/axes,
  and reserve space to minimize visible shift.
- Profile under representative CPU/network constraints and disable extensions
  that distort measurements.

## Theme, visual design, and browser behavior

- Verify supported light/dark and product themes, including native controls,
  scrollbars, and browser theme color.
- Set `color-scheme` consistently with the active theme.
- Give native selects explicit readable colors across platforms.
- Check foreground/background contrast and non-color status cues.
- Increase clarity/contrast for hover, active, and focus states rather than
  making interaction states less visible.
- Keep borders, shadows, radii, icon weight, and surface hierarchy consistent
  with neighboring product UI.
- Align elements deliberately to edges, baselines, grids, or optical centers.
- Use nested radii that appear concentric and avoid excessive elevation layers.
- Make charts legible for common color-vision differences and provide text or
  structural equivalents for essential values.

## React and hydration safety

- A controlled input with `value` needs a corresponding change contract; use a
  default value for genuinely uncontrolled initialization.
- Ensure hydration does not replace an active input, lose typed text, or move
  focus.
- Guard locale/time-dependent output so server and client do not disagree.
- Use hydration-warning suppression only for a known, unavoidable mismatch and
  keep its scope narrow.
- Do not read layout geometry, storage, or browser globals during server render.
- Keep loading skeleton geometry close to final content to avoid shift.
- For deeper React performance concerns, read
  [React and Next performance](./react-next-performance.md).

## Report findings

Group findings by file. Use `file:line` when the artifact has stable lines.
For each finding, include severity, observed evidence, and the smallest credible
fix. Keep the report terse and omit generic praise or a preamble.

```text
## src/components/AccountDialog.tsx

High — src/components/AccountDialog.tsx:42 — closing the dialog leaves focus on
the removed close button; return focus to the invoking control.
```

If no issue is found in a reviewed file, mark it as passing. Distinguish source
inspection from behavior actually exercised in a rendered interface.
