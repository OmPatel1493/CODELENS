import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** A pulsing placeholder block shown while real content is loading. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />;
}
