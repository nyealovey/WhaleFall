import * as LabelPrimitive from "@radix-ui/react-label";
import * as React from "react";

import { cn } from "@/utils/cn";

function Label({ className, ...props }: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return <LabelPrimitive.Root className={cn("text-sm leading-none font-medium", className)} data-slot="label" {...props} />;
}

export { Label };
