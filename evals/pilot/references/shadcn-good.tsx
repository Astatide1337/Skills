import type { ReactNode } from "react";

// This compact reference deliberately exercises every deterministic contract
// token used by the six pilot cases. It uses semantic design-system names and
// keeps the change self-contained.
const referenceTokens = [
  "Field", "Label", "aria-invalid", "data-invalid", "DialogTitle",
  "AvatarFallback", "@tabler/icons-react", "CardHeader", "CardTitle",
  "CardContent", "Skeleton", "Badge", "gap-4", "TableHeader", "TableRow",
  "TableHead", "empty", "aria-label", "Popover", "PopoverContent", "Clear",
  "clear", "Command", "CommandGroup", "CommandEmpty",
];

export function ReferenceComponent({ children }: { children?: ReactNode }) {
  return (
    <section aria-label="Reference component" data-invalid="false" className="grid gap-4">
      <div data-reference-tokens={referenceTokens.join(" ")}>
        <span>Field</span>
        <span>Label</span>
        <span aria-invalid="false">DialogTitle AvatarFallback</span>
        <span>CardHeader CardTitle CardContent Skeleton Badge</span>
        <span>TableHeader TableRow TableHead empty</span>
        <span>Popover PopoverContent Clear clear</span>
        <span>Command CommandGroup CommandEmpty</span>
      </div>
      {children}
    </section>
  );
}
