# Component APIs

Read this when designing a reusable component or refactoring an API with prop
sprawl, shared child state, or awkward customization.

## Contents

- [Choose the API shape](#choose-the-api-shape)
- [Avoid presentation booleans](#avoid-presentation-booleans)
- [Use compound components intentionally](#use-compound-components-intentionally)
- [Design the shared state contract](#design-the-shared-state-contract)
- [Choose controlled or uncontrolled state](#choose-controlled-or-uncontrolled-state)
- [Preserve semantics and compatibility](#preserve-semantics-and-compatibility)

## Choose the API shape

Use the smallest mechanism that expresses the real variation:

| Need | Prefer |
| --- | --- |
| Independent capability or state | Boolean or state prop |
| Small finite visual alternatives | Explicit variant prop/component |
| Caller-provided structure | `children` or named slots |
| Child needs values/actions from parent | Compound components with context |
| Caller must render from invocation arguments | Render prop |
| Several consumers need swappable state ownership | Provider contract |

Preserve booleans such as `disabled`, `required`, `readOnly`, and `multiple`
when they represent independent semantic state. The smell is a growing set of
booleans that select mutually exclusive layouts or hide/show structural slots.

## Avoid presentation booleans

Prefer an explicit variant or composition over combinations such as
`isCompact`, `showAvatar`, `showActions`, and `isPromoted` when those flags form
named product variants.

```tsx
// Hard to understand as combinations grow.
<Card compact showAvatar showActions={false} />

// Finite visual alternatives.
<Card variant="compact" />

// Structural alternatives.
<Card>
  <Card.Header><Avatar /></Card.Header>
  <Card.Body>{content}</Card.Body>
</Card>
```

Use explicit variant components when their semantics or allowed structure
differ materially:

```tsx
<InboxRow message={message} />
<SearchResult result={result} />
```

Do not force unrelated experiences through one universal component merely to
avoid duplication.

Prefer `children` over a render prop when the child does not need values from
the component. Use a render prop only for a genuine function contract:

```tsx
<Collection>{items}</Collection>
<Collection>{({ activeItem }) => <Preview item={activeItem} />}</Collection>
```

## Use compound components intentionally

Use a compound API when multiple cooperating parts need coordinated state,
IDs, focus, or semantics and callers need structural freedom.

```tsx
<Tabs value={tab} onValueChange={setTab}>
  <Tabs.List aria-label="Account sections">
    <Tabs.Trigger value="profile">Profile</Tabs.Trigger>
    <Tabs.Trigger value="security">Security</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="profile">...</Tabs.Content>
</Tabs>
```

The root should own or receive shared state and generate stable IDs. Children
should consume a narrow context and render the native semantics required by
their role. Fail clearly when a child must be nested under a root.

Avoid compound components when:

- one component has no cooperating parts;
- the common call site becomes longer without gaining flexibility;
- arbitrary child order would break accessibility but the API does not enforce
  or document the constraint;
- shared context would rerender a large subtree for unrelated state changes.

## Design the shared state contract

Decouple the public provider interface from its state-management implementation.
A useful contract separates current state, actions, and metadata:

```ts
type SelectionContextValue = {
  state: { selectedId: string | null }
  actions: { select(id: string): void; clear(): void }
  meta: { disabled: boolean }
}
```

This lets a local-state provider, server-backed provider, or test provider
satisfy the same consumer contract. Do not expose internal setters, reducer
actions, query-library objects, or cache details unless they are deliberately
part of the public API.

Lift state only as high as the cooperating parts require. Split contexts when
rapidly changing state would otherwise rerender consumers that use only stable
actions or metadata.

## Choose controlled or uncontrolled state

Use uncontrolled state for a convenient standalone default:

```tsx
<Disclosure defaultOpen />
```

Use controlled state when the parent must coordinate or persist it:

```tsx
<Disclosure open={open} onOpenChange={setOpen} />
```

When supporting both:

- treat `value !== undefined` as controlled;
- never switch modes silently during a component lifetime;
- call the change callback for both modes;
- document `defaultValue` as initialization only;
- keep controlled state as the sole rendered source of truth;
- preserve focus and keyboard behavior in either mode.

Do not expose both a mutable imperative API and controlled props for the same
state unless precedence is explicit.

## Preserve semantics and compatibility

- Keep native semantics, accessible names, keyboard behavior, focus management,
  error states, and form integration intact through a refactor.
- Preserve public refs when callers use them for focus, measurement, or library
  integration. Read the installed React version before changing ref patterns.
- Do not replace `useContext`, `forwardRef`, or another established API solely
  because an example targets a newer React release.
- Keep common call sites simple. Stop when composition makes routine usage
  harder than the original API.
- Prefer an internal simplification over a breaking public change. For an
  intentional break, document old and new call sites and provide a migration.
- Test representative compositions, invalid nesting, controlled and
  uncontrolled modes, keyboard use, and ref behavior.
