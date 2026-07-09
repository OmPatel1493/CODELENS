import { FolderGit2, Search, Bug } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const STATS = [
  { label: "Repositories", value: "0", icon: FolderGit2 },
  { label: "Indexed chunks", value: "0", icon: Search },
  { label: "Searches run", value: "0", icon: Bug },
];

export function DashboardPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Connect a repository to start searching and localizing bugs.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {STATS.map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription>{label}</CardDescription>
              <Icon className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <CardTitle className="text-3xl">{value}</CardTitle>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Get started</CardTitle>
          <CardDescription>
            Repository ingestion, semantic search, and bug localization plug in
            here as each milestone lands.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
