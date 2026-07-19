import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Search as SearchIcon, Loader2, FileCode } from "lucide-react";

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
  searchRepository,
  type SearchHit,
} from "@/lib/api";

const EXAMPLES = [
  "Where is authentication implemented?",
  "How are API routes defined?",
  "Where is input validation handled?",
];

function scoreColor(score: number): string {
  if (score >= 0.6) return "bg-green-500/15 text-green-600 dark:text-green-400";
  if (score >= 0.4) return "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400";
  return "bg-muted text-muted-foreground";
}

function ResultCard({ hit }: { hit: SearchHit }) {
  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
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
        <Badge variant="secondary" className={cn("ml-auto", scoreColor(hit.score))}>
          {Math.round(hit.score * 100)}% match
        </Badge>
      </div>
      <CodeBlock code={hit.snippet} filePath={hit.file_path} />
    </div>
  );
}

export function SearchPage() {
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

  const search = useMutation({
    mutationFn: (q: string) => searchRepository(Number(repoId), q),
  });

  function runSearch(q: string) {
    if (repoId && q.trim()) search.mutate(q);
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-sm text-muted-foreground">
          Ask about the codebase in plain English.
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
              runSearch(query);
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
              placeholder="e.g. where is JWT authentication implemented?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={search.isPending || !query.trim()}>
              {search.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <SearchIcon className="size-4" />
              )}
              Search
            </Button>
          </form>

          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQuery(ex);
                  runSearch(ex);
                }}
                className="rounded-full border px-3 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                {ex}
              </button>
            ))}
          </div>

          {search.isError && (
            <p role="alert" className="text-sm text-destructive">
              {search.error instanceof ApiError
                ? search.error.message
                : "Search failed. Try again."}
            </p>
          )}

          {search.isSuccess && search.data.results.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No matches for “{search.data.query}”.
            </p>
          )}

          <div className="space-y-4">
            {search.data?.results.map((hit) => (
              <ResultCard key={hit.chunk_id} hit={hit} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
