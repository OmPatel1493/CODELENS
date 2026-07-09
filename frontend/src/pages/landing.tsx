import { Link } from "react-router-dom";
import { ScanSearch, Search, Bug, FolderGit2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

const FEATURES = [
  {
    icon: Search,
    title: "Semantic code search",
    body: "Ask in plain English — “where is JWT auth implemented?” — and get ranked, explained results.",
  },
  {
    icon: Bug,
    title: "Bug localization",
    body: "Paste a stack trace and surface the most likely source files, with reasoning.",
  },
  {
    icon: FolderGit2,
    title: "Structural indexing",
    body: "Files, classes, and functions parsed with tree-sitter for language-aware search.",
  },
];

export function LandingPage() {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <header className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <div className="flex items-center gap-2 font-semibold">
          <ScanSearch className="size-5 text-primary" />
          CodeLens
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button render={<Link to="/login" />} variant="ghost">
            Sign in
          </Button>
          <Button render={<Link to="/app" />}>Get started</Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6">
        <section className="py-20 text-center">
          <h1 className="mx-auto max-w-3xl text-balance text-5xl font-semibold tracking-tight">
            Understand any codebase in plain English
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            CodeLens indexes a repository, answers natural-language questions
            about the code, and localizes bugs from stack traces — with an
            explanation for every result.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <Button render={<Link to="/app" />} size="lg">
              Try the dashboard
            </Button>
            <Button render={<Link to="/login" />} size="lg" variant="outline">
              Sign in
            </Button>
          </div>
        </section>

        <section className="grid gap-6 pb-24 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-lg border p-6 text-left">
              <Icon className="size-6 text-primary" />
              <h3 className="mt-4 font-medium">{title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
