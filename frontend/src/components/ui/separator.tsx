import * as React from "react";

import { cn } from "@/utils/cn";

function Separator({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="separator" className={cn("bg-border h-px w-full", className)} {...props} />;
}

export { Separator };
