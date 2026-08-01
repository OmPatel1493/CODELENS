import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { BookOpen, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  ApiError,
  explainRepository,
  listRepoFiles,
  listRepositories,
} from "@/lib/api";

export function ExplainPage() {
  const { data: repos } = useQuery({
    queryKey: ["repositories"],
    queryFn: listRepositories,
  });
  const ready = repos?.filter((r) => r.status === "ready") ?? [];

  const [repoId, setRepoId] = useState("");
  const [scope, setScope] = useState<"repo" | "file">("repo");
  const [file, setFile] = useState("");

  useEffect(() => {
    if (!repoId && ready.length > 0) setRepoId(String(ready[0].id));
  }, [ready, repoId]);

  const { data: files } = useQuery({
    queryKey: ["repo-files", repoId],
    queryFn: () => listRepoFiles(Number(repoId)),
    enabled: !!repoId && scope === "file",
  });

  const explain = useMutation({
    mutationFn: () =>
      explainRepository(
        Number(repoId),
        scope === "file" ? { scope: "file", file } : { scope: "repo" },
      ),
  });

  const canSubmit = repoId && (scope === "repo" || file);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Explain</h1>
        <p className="text-sm text-muted-foreground">
          A plain-English explanation of the code — written for non-programmers.
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
                {(["repo", "file"] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setScope(s)}
                    className={cn(
                      "rounded px-3 py-1",
                      scope === s
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {s === "repo" ? "Whole project" : "A file"}
                  </button>
                ))}
              </div>
            </div>

            {scope === "file" && (
              <Select items={{}} value={file} onValueChange={(v) => setFile(v ?? "")}>
                <SelectTrigger className="w-full sm:w-96">
                  <SelectValue placeholder="Choose a file…" />
                </SelectTrigger>
                <SelectContent>
                  {(files ?? []).map((f) => (
                    <SelectItem key={f} value={f}>
                      {f}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            <Button
              type="button"
              onClick={() => explain.mutate()}
              disabled={explain.isPending || !canSubmit}
              className="sm:w-44"
            >
              {explain.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <BookOpen className="size-4" />
              )}
              Explain in plain English
            </Button>
          </div>

          {explain.isError && (
            <p role="alert" className="text-sm text-destructive">
              {explain.error instanceof ApiError
                ? explain.error.message
                : "Couldn't generate an explanation. Try again."}
            </p>
          )}

          {explain.isPending && (
            <div className="space-y-4">
              <Skeleton className="h-7 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-11/12" />
              {[0, 1, 2].map((i) => (
                <div key={i} className="space-y-2 pt-2">
                  <Skeleton className="h-5 w-1/3" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-5/6" />
                </div>
              ))}
            </div>
          )}

          {explain.isSuccess && (
            <article className="space-y-6">
              <div className="space-y-2 rounded-lg border bg-muted/30 p-5">
                <div className="flex items-center gap-2 text-xs font-medium text-primary">
                  <Sparkles className="size-3.5" />
                  Plain-English explanation
                </div>
                <h2 className="text-xl font-semibold">{explain.data.title}</h2>
                <p className="leading-relaxed text-muted-foreground">
                  {explain.data.summary}
                </p>
              </div>

              {explain.data.sections.map((s, i) => (
                <section key={i} className="space-y-1.5">
                  <h3 className="font-medium">{s.heading}</h3>
                  <p className="whitespace-pre-wrap leading-relaxed text-muted-foreground">
                    {s.body}
                  </p>
                </section>
              ))}

              {explain.data.glossary.length > 0 && (
                <section className="space-y-3 rounded-lg border p-4">
                  <h3 className="text-sm font-medium">Words explained</h3>
                  <dl className="space-y-2">
                    {explain.data.glossary.map((g, i) => (
                      <div key={i} className="text-sm">
                        <dt className="inline font-medium">{g.term}: </dt>
                        <dd className="inline text-muted-foreground">{g.definition}</dd>
                      </div>
                    ))}
                  </dl>
                </section>
              )}
            </article>
          )}
        </>
      )}
    </div>
  );
}
