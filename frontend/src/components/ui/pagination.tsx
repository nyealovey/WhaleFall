import * as React from "react";

import { cn } from "@/utils/cn";

function Pagination({ className, ...props }: React.ComponentProps<"nav">) {
  return <nav aria-label="分页" className={cn("mx-auto flex w-full justify-center", className)} {...props} />;
}

function PaginationContent({ className, ...props }: React.ComponentProps<"ul">) {
  return <ul className={cn("flex flex-row items-center gap-1", className)} {...props} />;
}

function PaginationItem(props: React.ComponentProps<"li">) {
  return <li {...props} />;
}

function PaginationEllipsis({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span aria-hidden className={cn("flex size-8 items-center justify-center text-muted-foreground", className)} {...props}>
      ...
    </span>
  );
}

export { Pagination, PaginationContent, PaginationEllipsis, PaginationItem };
