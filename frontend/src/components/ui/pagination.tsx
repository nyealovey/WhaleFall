import * as React from "react";

import { cn } from "@/utils/cn";

function Pagination({ className, ...props }: React.ComponentProps<"nav">) {
  return <nav aria-label="分页" className={cn("mx-auto flex w-full justify-center", className)} {...props} />;
}

function PaginationContent({ className, ...props }: React.ComponentProps<"ul">) {
  return <ul className={cn("flex flex-row flex-nowrap items-center gap-1 whitespace-nowrap", className)} {...props} />;
}

function PaginationItem({ className, ...props }: React.ComponentProps<"li">) {
  return <li className={cn("shrink-0", className)} {...props} />;
}

function PaginationEllipsis({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span aria-hidden className={cn("flex size-8 shrink-0 items-center justify-center text-muted-foreground", className)} {...props}>
      ...
    </span>
  );
}

export { Pagination, PaginationContent, PaginationEllipsis, PaginationItem };
