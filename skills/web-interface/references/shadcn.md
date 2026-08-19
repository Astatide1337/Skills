# shadcn Projects

Read this when the user explicitly requests shadcn or the repository has
`components.json`. Read [shadcn operations](./shadcn-operations.md) as well when
the task uses the CLI, a registry, or a preset.

## Contents

- [Inspect project context](#inspect-project-context)
- [Select and compose components](#select-and-compose-components)
- [Follow component contracts](#follow-component-contracts)
- [Style within the system](#style-within-the-system)
- [Handle forms, icons, and feedback](#handle-forms-icons-and-feedback)
- [Review the result](#review-the-result)

## Inspect project context

Treat the local project as the source of truth. Read:

- `components.json`, including style/base, RSC mode, aliases, CSS path,
  configured registries, and icon library when present;
- the lockfile and `packageManager` field;
- installed UI component files and their exports;
- global CSS, theme variables, Tailwind version/configuration, and utility
  merger;
- neighboring usage examples in the actual application.

Do not assume:

- imports start with `@/`;
- the project uses Lucide icons;
- components use Radix rather than Base UI, React Aria, or another primitive;
- Tailwind v3 and v4 configuration are interchangeable;
- a registry item is already installed;
- upstream and locally modified component files are identical.

When `components.json` is absent, do not impose shadcn conventions merely
because the project uses React and Tailwind.

## Select and compose components

Reuse an installed component and its supported variants before creating custom
markup. Choose by behavior and semantics, not visual resemblance:

| Need | Typical component |
| --- | --- |
| Action | Button |
| Text or structured input | Input, Textarea, Select, Combobox, Checkbox, RadioGroup, Switch |
| Small finite option set | ToggleGroup |
| Navigation | Link plus Breadcrumb, Tabs, NavigationMenu, Sidebar, or Pagination |
| Modal decision | Dialog or AlertDialog |
| Supplemental side/bottom surface | Sheet or Drawer |
| Menu actions | DropdownMenu, ContextMenu, or Menubar |
| Status or feedback | Alert, Badge, Progress, Skeleton, Spinner, or project toast |
| Empty result | Empty |
| Data display | Table, Card, Avatar, or Chart |
| Command selection | Command, commonly within Dialog |
| Separation or scroll containment | Separator, ScrollArea, Resizable |

Do not substitute a component solely to achieve a visual effect. For example,
use AlertDialog for a destructive confirmation, not an ordinary Dialog with
manually recreated semantics.

## Follow component contracts

- Keep item components inside the required group/list container. Examples:
  `SelectItem` in `SelectGroup`, `TabsTrigger` in `TabsList`, and command/menu
  items in their group where the installed API requires it.
- Give Dialog, Sheet, Drawer, and AlertDialog an accessible title. Visually hide
  the title only when another visible label clearly supplies the same context.
- Include Avatar fallback content.
- Use the installed Card parts to communicate header, description, content,
  and footer structure instead of placing everything in one undifferentiated
  region.
- Preserve trigger/content relationships, portals, positioning, focus handling,
  and state attributes supplied by the primitive.
- Use the primitive's installed composition mechanism: `asChild` for the Radix
  form or `render`/the documented equivalent for the selected base. Do not mix
  APIs from another base.
- Avoid nested interactive elements when composing triggers with links or
  buttons.
- Keep controlled/uncontrolled usage aligned with the installed component's
  contract; do not invent `isOpen` when it uses `open` and `onOpenChange`.

## Style within the system

- Use semantic tokens such as background, foreground, muted, destructive,
  border, and ring roles instead of raw brand hues.
- Use built-in `variant` and `size` options before overriding component
  typography, color, radius, or state styles.
- Use the project's class merge helper for conditional classes.
- Prefer `gap-*` in flex/grid layouts over margin choreography or `space-*`
  when children can be conditional or wrap.
- Use a combined size utility when width and height are equal if that convention
  exists in the project's Tailwind version.
- Use the project's truncation utility and give flex children `min-w-0` when
  necessary.
- Avoid manual dark-mode color duplication when semantic tokens already define
  theme behavior.
- Avoid arbitrary z-index overrides on overlays; diagnose portal and stacking
  context problems first.
- Keep `className` overrides focused on placement and supported extension
  points. If every call site rewrites a component's appearance, add a coherent
  local variant instead.

## Handle forms, icons, and feedback

- Use the installed field primitives and group related controls with the
  project's FieldGroup/FieldSet pattern when available.
- Keep labels, descriptions, messages, and controls associated by the component
  API. Apply `aria-invalid` to the control and any required invalid-state data
  attribute to its field wrapper.
- Use the installed input-group parts rather than nesting a raw input and button
  inside arbitrary markup.
- Use a ToggleGroup for a small mutually exclusive option set when its semantics
  match; do not simulate it with unrelated buttons and manual selected state.
- Use the icon package named by project configuration or existing code. Match
  the installed component's icon slot/data attribute convention and do not add
  redundant sizing classes when the component already controls icon size.
- Compose a loading button with the installed Spinner and preserve its original
  label where possible. Disable while an irreversible request is in flight;
  do not assume an undocumented `isLoading` prop.
- Use the project's installed toast system. Do not mix APIs from a different
  primitive base.

## Review the result

After any generated or registry-supplied code enters the repository:

1. Read every added or changed file.
2. Check aliases, import paths, package dependencies, client/server boundaries,
   icon library, and Tailwind syntax.
3. Check primitive composition, required labels/titles/groups/fallbacks, focus,
   keyboard behavior, and form semantics.
4. Replace raw colors or incompatible styles with the local semantic system.
5. Compare local modifications before accepting an upstream update.
6. Render and exercise the affected states.

This catalog does not itself authorize a network fetch or package mutation.
When required local configuration or an approved registry snapshot is missing,
state the missing evidence rather than inventing shadcn context.
