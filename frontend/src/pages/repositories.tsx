import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderGit2, GitBranch, Trash2, Upload, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  ApiError,
  deleteRepository,
  ingestGithubRepo,
  listRepositories,
  uploadRepository,
  type RepoStatus,
  type Repository,
} from "@/lib/api";

const STATUS_STYLES: Record<RepoStatus, string> = {
  ready: "bg-green-500/15 text-green-600 dark:text-green-400",
  failed: "bg-destructive/15 text-destructive",
  pending: "bg-muted text-muted-foreground",
  indexing: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
};

function StatusBadge({ status }: { status: RepoStatus }) {
  const active = status === "pending" || status === "indexing";
  return (
    <Badge variant="secondary" className={cn("gap-1", STATUS_STYLES[status])}>
      {active && <Loader2 className="size-3 animate-spin" />}
      {status}
    </Badge>
  );
}

function AddRepoForm() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"github" | "upload">("github");
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["repositories"] });

  const githubMutation = useMutation({
    mutationFn: () => ingestGithubRepo(url),
    onSuccess: () => {
      setUrl("");
      invalidate();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Failed to add repository"),
  });

  const uploadMutation = useMutation({
    mutationFn: () => uploadRepository(name, file as File),
    onSuccess: () => {
      setName("");
      setFile(null);
      invalidate();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Upload failed"),
  });

  const pending = githubMutation.isPending || uploadMutation.isPending;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "github") githubMutation.mutate();
    else if (file) uploadMutation.mutate();
    else setError("Choose a .zip file to upload");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a repository</CardTitle>
        <CardDescription>
          Index a public GitHub repo or upload a .zip of your code.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Button
            type="button"
            variant={mode === "github" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("github")}
          >
            <GitBranch className="size-4" /> GitHub URL
          </Button>
          <Button
            type="button"
            variant={mode === "upload" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("upload")}
          >
            <Upload className="size-4" /> Upload .zip
          </Button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          {mode === "github" ? (
            <div className="space-y-2">
              <Label htmlFor="url">Repository URL</Label>
              <Input
                id="url"
                placeholder="https://github.com/owner/repo"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
              />
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="my-project"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="file">Archive (.zip)</Label>
                <Input
                  id="file"
                  type="file"
                  accept=".zip"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  required
                />
              </div>
            </div>
          )}

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          <Button type="submit" disabled={pending}>
            {pending ? "Adding…" : "Add repository"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function RepoRow({ repo }: { repo: Repository }) {
  const queryClient = useQueryClient();
  const del = useMutation({
    mutationFn: () => deleteRepository(repo.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["repositories"] }),
  });

  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {repo.source === "github" ? (
            <GitBranch className="size-4 shrink-0 text-muted-foreground" />
          ) : (
            <Upload className="size-4 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate font-medium">{repo.name}</span>
          <StatusBadge status={repo.status} />
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {repo.status === "ready"
            ? `${repo.file_count} files indexed`
            : repo.status === "failed"
              ? (repo.error_message ?? "Ingestion failed")
              : "Processing…"}
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label={`Delete ${repo.name}`}
        onClick={() => del.mutate()}
        disabled={del.isPending}
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}

export function RepositoriesPage() {
  const { data: repos, isLoading, isError } = useQuery({
    queryKey: ["repositories"],
    queryFn: listRepositories,
    // Poll while anything is still processing, so status flips to ready live.
    refetchInterval: (query) =>
      query.state.data?.some((r) => r.status === "pending" || r.status === "indexing")
        ? 2000
        : false,
    // Keep polling even when the tab is unfocused (status resolves in seconds).
    refetchIntervalInBackground: true,
  });

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Repositories</h1>
        <p className="text-sm text-muted-foreground">
          Connect a codebase to index it for search and bug localization.
        </p>
      </div>

      <AddRepoForm />

      <div className="space-y-3">
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {isError && (
          <p className="text-sm text-destructive">Couldn’t load repositories.</p>
        )}
        {repos?.length === 0 && (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-10 text-center">
            <FolderGit2 className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No repositories yet. Add one above to get started.
            </p>
          </div>
        )}
        {repos?.map((repo) => <RepoRow key={repo.id} repo={repo} />)}
      </div>
    </div>
  );
}
