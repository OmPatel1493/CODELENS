import { useQuery } from "@tanstack/react-query";
import { FolderGit2, Search, Bug } from "lucide-react";
import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getRepositoryStats } from "@/lib/api";

export function DashboardPage() {
  const { data: stats } = useQuery({
    queryKey: ["repository-stats"],
    queryFn: getRepositoryStats,
  });

  const tiles = [
    { label: "Repositories", value: stats?.repositories ?? 0, icon: FolderGit2 },
    { label: "Indexed chunks", value: stats?.indexed_chunks ?? 0, icon: Search },
    { label: "Searches run", value: 0, icon: Bug },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Connect a repository to start searching and localizing bugs.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {tiles.map(({ label, value, icon: Icon }) => (
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
            Add a repository to index its code, then search it in plain English.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button render={<Link to="/app/repositories" />} nativeButton={false}>
            Add a repository
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
