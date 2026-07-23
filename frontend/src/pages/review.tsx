import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GitPullRequest, Loader2, FileCode, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CodeBlock } from "@/components/code-block";
import { cn } from "@/lib/utils";
import {
  ApiError,
  listRepositories,
  reviewRepository,
  type ReviewComment,
  type SearchHit,
} from "@/lib/api";

const EXAMPLE_PR = "https://github.com/pallets/itsdangerous/pull/366";

function severityColor(sev: string): string {
  switch (sev.toLowerCase()) {
    case "high":
      return "bg-red-500/15 text-red-600 dark:text-red-400";
    case "medium":
      return "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400";
    case "low":
      return "bg-blue-500/15 text-blue-600 dark:text-blue-400";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function CommentCard({ c }: { c: ReviewComment }) {
  return (
    <div className="space-y-1 rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className={cn("uppercase", severityColor(c.severity))}>
          {c.severity}
        </Badge>
        {c.file && (
          <span className="font-mono text-sm">
            {c.file}
            {c.line != null && `:${c.line}`}
          </span>
        )}
      </div>
      <p className="text-sm leading-relaxed">{c.comment}</p>
    </div>
  );
}

function SourceCard({ index, hit }: { index: number; hit: SearchHit }) {
  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="font-mono">
          [{index}]
        </Badge>
        <FileCode className="size-4 shrink-0 text-muted-foreground" />
        <span className="font-mono text-sm">{hit.file_path}</span>
        {hit.symbol_name && (
          <span className="font-mono text-sm font-medium text-primary">
            {hit.symbol_name}
          </span>
        )}
      </div>
      <CodeBlock code={hit.snippet} filePath={hit.file_path} />
    </div>
  );
}

export function ReviewPage() {
  const { data: repos } = useQuery({
    queryKey: ["repositories"],
    queryFn: listRepositories,
  });
  const ready = repos?.filter((r) => r.status === "ready") ?? [];

  const [repoId, setRepoId] = useState("");
  const [mode, setMode] = useState<"pr" | "diff">("pr");
  const [prUrl, setPrUrl] = useState("");
  const [diff, setDiff] = useState("");

  useEffect(() => {
    if (!repoId && ready.length > 0) setRepoId(String(ready[0].id));
  }, [ready, repoId]);

  const review = useMutation({
    mutationFn: () =>
      reviewRepository(
        Number(repoId),
        mode === "pr" ? { pr_url: prUrl } : { diff },
      ),
  });

  const canSubmit = repoId && (mode === "pr" ? prUrl.trim() : diff.trim());

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Code Review</h1>
        <p className="text-sm text-muted-foreground">
          Review a GitHub PR or a raw diff — findings are grounded in the indexed codebase.
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
          <div className="flex flex-col gap-3">
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

              <div className="flex rounded-md border p-0.5 text-sm">
                {(["pr", "diff"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={cn(
                      "rounded px-3 py-1",
                      mode === m
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {m === "pr" ? "GitHub PR URL" : "Paste diff"}
                  </button>
                ))}
              </div>
            </div>

            {mode === "pr" ? (
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  placeholder="https://github.com/owner/repo/pull/123"
                  value={prUrl}
                  onChange={(e) => setPrUrl(e.target.value)}
                  className="flex-1"
                />
                <button
                  type="button"
                  onClick={() => setPrUrl(EXAMPLE_PR)}
                  className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  try an example
                </button>
              </div>
            ) : (
              <textarea
                placeholder="Paste a unified diff (git diff output)…"
                value={diff}
                onChange={(e) => setDiff(e.target.value)}
                rows={10}
                className="w-full rounded-md border bg-transparent p-3 font-mono text-xs"
              />
            )}

            <Button
              type="button"
              onClick={() => review.mutate()}
              disabled={review.isPending || !canSubmit}
              className="sm:w-40"
            >
              {review.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <GitPullRequest className="size-4" />
              )}
              Review
            </Button>
          </div>

          {review.isError && (
            <p role="alert" className="text-sm text-destructive">
              {review.error instanceof ApiError
                ? review.error.message
                : "Review failed. Try again."}
            </p>
          )}

          {review.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Fetching the diff, retrieving related code, and reviewing…
            </div>
          )}

          {review.isSuccess && (
            <div className="space-y-6">
              <div className="space-y-2 rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <GitPullRequest className="size-4 text-primary" />
                  Summary
                </div>
                <p className="text-sm leading-relaxed">{review.data.summary}</p>
              </div>

              {review.data.comments.length === 0 ? (
                <div className="flex items-center gap-2 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
                  <CheckCircle2 className="size-4 text-green-500" />
                  No issues flagged — the change looks clean.
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">
                    {review.data.comments.length} finding
                    {review.data.comments.length === 1 ? "" : "s"}
                  </p>
                  {review.data.comments.map((c, i) => (
                    <CommentCard key={i} c={c} />
                  ))}
                </div>
              )}

              {review.data.sources.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">Context used</p>
                  {review.data.sources.map((hit, i) => (
                    <SourceCard key={hit.chunk_id} index={i + 1} hit={hit} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
