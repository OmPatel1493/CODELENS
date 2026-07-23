import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Sparkles, Loader2, FileCode } from "lucide-react";

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
import {
  ApiError,
  askRepository,
  listRepositories,
  type SearchHit,
} from "@/lib/api";

const EXAMPLES = [
  "How does authentication work in this codebase?",
  "What does the main entry point do?",
  "How is configuration loaded?",
];

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
        <Badge variant="secondary">{hit.kind}</Badge>
        <span className="text-xs text-muted-foreground">
          lines {hit.start_line}–{hit.end_line}
        </span>
      </div>
      <CodeBlock code={hit.snippet} filePath={hit.file_path} />
    </div>
  );
}

export function AskPage() {
  const { data: repos } = useQuery({
    queryKey: ["repositories"],
    queryFn: listRepositories,
  });
  const ready = repos?.filter((r) => r.status === "ready") ?? [];

  const [repoId, setRepoId] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!repoId && ready.length > 0) setRepoId(String(ready[0].id));
  }, [ready, repoId]);

  const ask = useMutation({
    mutationFn: (q: string) => askRepository(Number(repoId), q),
  });

  function runAsk(q: string) {
    if (repoId && q.trim()) ask.mutate(q);
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ask</h1>
        <p className="text-sm text-muted-foreground">
          Ask a question and get a cited answer, grounded in the indexed code.
        </p>
      </div>

      {ready.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-10 text-center">
          <p className="text-sm text-muted-foreground">
            No indexed repositories yet.
          </p>
          <Button render={<Link to="/app/repositories" />} nativeButton={false}>
            Add a repository
          </Button>
        </div>
      ) : (
        <>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              runAsk(query);
            }}
            className="flex flex-col gap-3 sm:flex-row"
          >
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
            <Input
              placeholder="e.g. how does authentication work?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={ask.isPending || !query.trim()}>
              {ask.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              Ask
            </Button>
          </form>

          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQuery(ex);
                  runAsk(ex);
                }}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                {ex}
              </button>
            ))}
          </div>

          {ask.isError && (
            <p role="alert" className="text-sm text-destructive">
              {ask.error instanceof ApiError
                ? ask.error.message
                : "Answer generation failed. Try again."}
            </p>
          )}

          {ask.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Retrieving relevant code and composing an answer…
            </div>
          )}

          {ask.isSuccess && (
            <div className="space-y-6">
              <div className="space-y-2 rounded-lg border bg-muted/30 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Sparkles className="size-4 text-primary" />
                  Answer
                </div>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {ask.data.answer}
                </div>
              </div>

              {ask.data.sources.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-muted-foreground">
                    Sources
                  </p>
                  {ask.data.sources.map((hit, i) => (
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
