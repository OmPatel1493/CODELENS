import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { BarChart3, Loader2, CheckCircle2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ApiError,
  evaluateRepository,
  listRepositories,
  type EvalCase,
} from "@/lib/api";

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-2xl font-semibold tabular-nums">
        {(value * 100).toFixed(0)}
        <span className="text-base text-muted-foreground">%</span>
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function CaseRow({ c }: { c: EvalCase }) {
  const hit = c.found_rank > 0;
  return (
    <div className="flex items-center gap-3 border-b py-2 text-sm last:border-0">
      {hit ? (
        <CheckCircle2 className="size-4 shrink-0 text-green-500" />
      ) : (
        <XCircle className="size-4 shrink-0 text-red-500" />
      )}
      <span className="flex-1">{c.query}</span>
      <span className="font-mono text-xs text-muted-foreground">
        {c.expected.join(", ")}
      </span>
      <Badge variant="secondary" className="tabular-nums">
        {hit ? `rank ${c.found_rank}` : "miss"}
      </Badge>
    </div>
  );
}

export function EvaluationPage() {
  const { data: repos } = useQuery({
    queryKey: ["repositories"],
    queryFn: listRepositories,
  });
  const ready = repos?.filter((r) => r.status === "ready") ?? [];

  const [repoId, setRepoId] = useState("");
  useEffect(() => {
    if (!repoId && ready.length > 0) setRepoId(String(ready[0].id));
  }, [ready, repoId]);

  const evalRun = useMutation({
    mutationFn: () => evaluateRepository(Number(repoId)),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Retrieval Evaluation</h1>
        <p className="text-sm text-muted-foreground">
          Run a hand-labeled benchmark against the live retriever — Recall@k, MRR, MAP.
        </p>
      </div>

      {ready.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-10 text-center">
          <p className="text-sm text-muted-foreground">No indexed repositories yet.</p>
          <Button render={<Link to="/app/repositories" />} nativeButton={false}>
            Add a repository
          </Button>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Select
              items={Object.fromEntries(ready.map((r) => [String(r.id), r.name]))}
              value={repoId}
              onValueChange={(v) => setRepoId(v ?? "")}
            >
              <SelectTrigger className="sm:w-56">
                <SelectValue placeholder="Repository" />
              </SelectTrigger>
              <SelectContent>
                {ready.map((r) => (
                  <SelectItem key={r.id} value={String(r.id)}>
                    {r.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              onClick={() => evalRun.mutate()}
              disabled={evalRun.isPending || !repoId}
            >
              {evalRun.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <BarChart3 className="size-4" />
              )}
              Run benchmark
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            A labeled query set ships for <span className="font-mono">itsdangerous</span> —
            index that repo to benchmark it. (More repos can be added to the benchmark.)
          </p>

          {evalRun.isError && (
            <p role="alert" className="text-sm text-destructive">
              {evalRun.error instanceof ApiError
                ? evalRun.error.message
                : "Evaluation failed. Try again."}
            </p>
          )}

          {evalRun.isSuccess && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Metric label="Recall@1" value={evalRun.data.summary.recall_at_1} />
                <Metric label="Recall@5" value={evalRun.data.summary.recall_at_5} />
                <Metric label="MRR" value={evalRun.data.summary.mrr} />
                <Metric label="MAP" value={evalRun.data.summary.map} />
              </div>
              <div className="rounded-lg border p-4">
                <p className="mb-2 text-sm font-medium text-muted-foreground">
                  {evalRun.data.summary.queries} labeled queries
                </p>
                {evalRun.data.per_query.map((c, i) => (
                  <CaseRow key={i} c={c} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
