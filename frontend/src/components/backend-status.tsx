/**
 * Small live indicator of API connectivity. Uses React Query so we get
 * loading/error/success states and automatic refetching for free.
 */

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

export function BackendStatus() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
  });

  const state = isLoading
    ? { color: "bg-yellow-500", label: "Connecting…" }
    : isError
      ? { color: "bg-red-500", label: "API offline" }
      : { color: "bg-green-500", label: `API ${data?.environment ?? "ok"}` };

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className={cn("size-2 rounded-full", state.color)} />
      {state.label}
    </div>
  );
}
