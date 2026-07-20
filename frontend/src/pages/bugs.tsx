import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Bug, Loader2, FileCode } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  localizeBug,
  type LocalizedFile,
} from "@/lib/api";

const EXAMPLE_TRACE = `Traceback (most recent call last):
  File "app/auth.py", line 42, in authenticate_user
    return create_token(user.id)
AttributeError: 'NoneType' object has no attribute 'id'`;

function scoreColor(score: number): string {
  if (score >= 0.6) return "bg-green-500/15 text-green-600 dark:text-green-400";
  if (score >= 0.4) return "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400";
  return "bg-muted text-muted-foreground";
}

function CandidateCard({ file, rank }: { file: LocalizedFile; rank: number }) {
  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">#{rank}</span>
        <FileCode className="size-4 shrink-0 text-muted-foreground" />
        <span className="font-mono text-sm">{file.file_path}</span>
        <span className="text-xs text-muted-foreground">
          lines {file.start_line}–{file.end_line}
        </span>
        <Badge variant="secondary" className={cn("ml-auto", scoreColor(file.score))}>
          {Math.round(file.score * 100)}% likely
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Why: </span>
        {file.reason}
      </p>
      <CodeBlock code={file.snippet} filePath={file.file_path} />
    </div>
  );
}

export function BugsPage() {
  const { data: repos } = useQuery({
    queryKey: ["repositories"],
    queryFn: listRepositories,
  });
  const ready = repos?.filter((r) => r.status === "ready") ?? [];

  const [repoId, setRepoId] = useState("");
  const [log, setLog] = useState("");

  useEffect(() => {
    if (!repoId && ready.length > 0) setRepoId(String(ready[0].id));
  }, [ready, repoId]);

  const localize = useMutation({
    mutationFn: () => localizeBug(Number(repoId), log),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Bug Localization</h1>
        <p className="text-sm text-muted-foreground">
          Paste a stack trace or error log — CodeLens ranks the files most likely
          responsible, and explains why.
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
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (repoId && log.trim()) localize.mutate();
            }}
            className="space-y-3"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
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
              <button
                type="button"
                onClick={() => setLog(EXAMPLE_TRACE)}
                className="self-start rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground sm:self-auto"
              >
                Try an example trace
              </button>
            </div>
            <textarea
              value={log}
              onChange={(e) => setLog(e.target.value)}
              rows={8}
              placeholder="Paste your stack trace or error log here…"
              className="w-full rounded-md border bg-transparent p-3 font-mono text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            />
            <Button type="submit" disabled={localize.isPending || !log.trim()}>
              {localize.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Bug className="size-4" />
              )}
              Localize bug
            </Button>
          </form>

          {localize.isError && (
            <p role="alert" className="text-sm text-destructive">
              {localize.error instanceof ApiError
                ? localize.error.message
                : "Localization failed. Try again."}
            </p>
          )}

          {localize.data && (
            <div className="space-y-4">
              {(localize.data.parsed.error_type || localize.data.parsed.message) && (
                <div className="rounded-lg border bg-muted/40 p-3 text-sm">
                  <span className="font-medium">Detected: </span>
                  {localize.data.parsed.error_type && (
                    <span className="font-mono">{localize.data.parsed.error_type}</span>
                  )}
                  {localize.data.parsed.message && (
                    <span className="text-muted-foreground">
                      {" "}
                      — {localize.data.parsed.message}
                    </span>
                  )}
                </div>
              )}
              {localize.data.results.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No likely files found. Try including more of the trace.
                </p>
              ) : (
                localize.data.results.map((file, i) => (
                  <CandidateCard key={file.file_path} file={file} rank={i + 1} />
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
