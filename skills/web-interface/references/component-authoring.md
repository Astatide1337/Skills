# Component Authoring

Read this when creating a reusable primitive, product component, block, or
design-system foundation. For prop/API architecture, also read
[Component APIs](./component-apis.md). This reference covers authoring inside an
application or design system; package publishing and marketplace distribution
remain outside this skill.

## Contents

- [Classify the artifact](#classify-the-artifact)
- [Start from semantics](#start-from-semantics)
- [Implement keyboard and focus behavior](#implement-keyboard-and-focus-behavior)
- [Expose state predictably](#expose-state-predictably)
- [Type native and custom props](#type-native-and-custom-props)
- [Use polymorphism sparingly](#use-polymorphism-sparingly)
- [Expose styling hooks](#expose-styling-hooks)
- [Build on semantic tokens](#build-on-semantic-tokens)
- [Document and verify the component](#document-and-verify-the-component)

## Classify the artifact

Name what is being built before choosing its API:

- **Primitive:** behavior and accessibility foundation with little product
  styling, such as Dialog, Tabs, or Tooltip.
- **Component:** reusable product/design-system unit, such as Button, Field, or
  StatusBadge.
- **Block:** composed product section, such as BillingTable or SignInForm.
- **Template:** page-level arrangement with replaceable content and behavior.

The lower the layer, the fewer product assumptions it should contain. Do not
give a primitive domain copy, routing, analytics, or server contracts. Do not
make a one-off product block infinitely configurable as if it were a primitive.

## Start from semantics

Choose the native element and interaction model before styling:

- Use `button` for actions and `a` for navigation.
- Use real labels and form controls so browser validation, autofill, submission,
  and accessible naming work.
- Use headings, lists, tables, fieldsets, and landmarks when their semantics
  match the content.
- Use ARIA to complete a pattern, not to replace an available native element.
- Keep the DOM order aligned with reading and keyboard order.

For a custom widget, identify the applicable WAI-ARIA interaction pattern and
implement its complete keyboard contract. A role without its behavior is not an
accessible component.

Every interactive component should define:

- accessible name and description;
- focus entry, movement, trapping, and restoration where applicable;
- keyboard activation and dismissal;
- disabled and read-only behavior;
- pending, invalid, expanded, selected, pressed, and checked states as relevant;
- touch target and pointer behavior;
- high-contrast, zoom, reduced-motion, and screen-reader behavior.

## Implement keyboard and focus behavior

- Use `:focus-visible` for a visible ring and never remove outline without an
  equivalent replacement.
- Keep focused elements unobscured by sticky regions and overlays.
- Move initial focus into modal interactions according to task priority; trap
  it only while modal; restore it to the invoking control on close.
- Support Escape where the interaction pattern expects dismissal.
- For composite widgets, choose roving `tabIndex` or `aria-activedescendant`
  deliberately and keep arrow-key behavior consistent with orientation.
- Keep Tab navigation for moving between components, not between every item in
  a composite widget unless the native pattern requires it.
- Announce async status with an appropriate live region without repeating
  noisy updates.
- Keep disabled controls discoverable when users need to understand why;
  `aria-disabled` may be more appropriate than removing them from focus, but
  block activation explicitly.

## Expose state predictably

Support controlled and uncontrolled use only when both are genuinely useful.
Keep one source of truth and one change event. See
[Component APIs](./component-apis.md) for the dual-mode contract.

Expose stable state for styling and testing with attributes:

```tsx
<button
  data-slot="accordion-trigger"
  data-state={open ? "open" : "closed"}
  aria-expanded={open}
>
  {children}
</button>
```

Use:

- `aria-*` for accessibility semantics;
- `data-state` for a finite behavioral/visual state;
- `data-disabled`, `data-invalid`, or `data-orientation` when styling a state
  shared across component parts;
- `data-slot` to identify stable subparts without relying on DOM position;
- props for caller configuration and event contracts.

Do not encode sensitive data, arbitrary user values, or rapidly changing
measurements in data attributes.

## Type native and custom props

Extend the native element's props so ordinary attributes and event types remain
available:

```ts
type ButtonProps = React.ComponentPropsWithoutRef<"button"> & {
  variant?: "primary" | "secondary" | "quiet"
}
```

When wrapping another component, derive from that component's public props
rather than copying them. Resolve name conflicts deliberately with `Omit` and a
documented replacement.

- Export public prop and state types that consumers reasonably compose.
- Keep variants as finite unions instead of free-form strings.
- Use discriminated unions when one mode requires different props.
- Preserve the ref element type when forwarding or accepting refs.
- Spread caller props in a deliberate order. Merge `className`, styles, event
  handlers, and IDs rather than accidentally replacing internal requirements.
- Compose event handlers so caller cancellation is respected when appropriate.
- Avoid `any` and excessively generic polymorphic signatures that make invalid
  HTML appear type-safe.

## Use polymorphism sparingly

Prefer a fixed semantic element when the component has fixed behavior. Use an
`as` or `asChild` mechanism only when consumers genuinely need to change the
rendered element without losing behavior or styling.

For `asChild`/slot composition, the child must:

- be exactly one concrete element;
- accept and spread the supplied props;
- merge event handlers and `className` correctly;
- accept the ref expected by the primitive;
- remain semantically appropriate for the behavior.

```tsx
<Button asChild>
  <a href="/settings">Settings</a>
</Button>
```

Do not produce nested interactive elements such as a button inside a button or
an anchor inside an anchor. Do not turn navigation into a button merely because
the visual component is named Button.

Use an `as` prop for simple typography/layout primitives with a controlled list
of elements. Use `asChild` when a behavior primitive must decorate an existing
element. Avoid either when separate explicit components communicate intent more
clearly.

## Expose styling hooks

- Use semantic variants for supported appearance, size, and state.
- Merge class names with the project's established utility; do not introduce a
  second merge system for one component.
- Use a variant utility such as CVA only when combinations are reused and its
  output remains understandable.
- Keep layout responsibility explicit: a component may own its internal layout,
  while the caller owns placement in surrounding layout.
- Avoid selectors based on fragile child position. Prefer `data-slot` and named
  parts for stable targeting.
- Preserve user overrides only where the public contract permits them; protect
  accessibility-critical styles such as hidden descriptions or focus behavior.

## Build on semantic tokens

Use semantic CSS variables or equivalent tokens instead of embedding raw theme
values throughout components:

```css
:root {
  --surface: oklch(1 0 0);
  --surface-foreground: oklch(0.18 0 0);
  --border-subtle: oklch(0.9 0 0);
}

[data-theme="dark"] {
  --surface: oklch(0.18 0 0);
  --surface-foreground: oklch(0.98 0 0);
  --border-subtle: oklch(0.32 0 0);
}
```

- Separate raw palette values from semantic roles when the system is large
  enough to benefit from both layers.
- Name roles by purpose (`surface`, `danger`, `focus-ring`) rather than current
  hue (`blue-500`).
- Keep foreground/background token pairs together and verify contrast.
- Define state tokens for hover, active, disabled, focus, and destructive use.
- Keep radius, spacing, typography, elevation, and motion scales coherent.
- Bind component variants to tokens; do not duplicate light/dark raw colors in
  every component.

## Document and verify the component

Document only the contract consumers need:

- purpose and when not to use it;
- import and minimal example;
- variants, state ownership, events, and refs;
- required composition and invalid nesting;
- accessibility behavior and labeling requirements;
- representative loading, empty, error, long-content, and responsive examples.

Verify:

1. native semantics and accessibility tree;
2. keyboard operation, focus entry/exit, and visible focus;
3. pointer and touch targets;
4. controlled and uncontrolled behavior where supported;
5. ref and form integration;
6. theme, high-contrast, reduced-motion, zoom, and responsive behavior;
7. short, long, translated, empty, loading, invalid, and disabled states;
8. public type behavior and representative compositions.
