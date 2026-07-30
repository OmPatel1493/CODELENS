import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Loader2, Network } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getDependencyGraph, listRepositories, type GraphNode } from "@/lib/api";

const W = 720;
const H = 520;
const PALETTE = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
  "#a855f7", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
];

interface Pos {
  x: number;
  y: number;
}

/** Fixed-iteration Fruchterman–Reingold force layout (computed once, no animation). */
function layout(nodes: GraphNode[], edges: { source: string; target: string }[]): Map<string, Pos> {
  const n = nodes.length;
  const pos = new Map<string, Pos>();
  nodes.forEach((node, i) => {
    // seed on a circle so the sim converges nicely
    const a = (2 * Math.PI * i) / Math.max(n, 1);
    pos.set(node.id, { x: W / 2 + Math.cos(a) * 200, y: H / 2 + Math.sin(a) * 200 });
  });
  if (n === 0) return pos;

  const area = W * H;
  const k = Math.sqrt(area / n); // ideal edge length
  let temp = W / 8;
  const iters = 300;

  for (let it = 0; it < iters; it++) {
    const disp = new Map<string, Pos>(nodes.map((nd) => [nd.id, { x: 0, y: 0 }]));

    // repulsion between every pair
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = pos.get(nodes[i].id)!;
        const b = pos.get(nodes[j].id)!;
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.hypot(dx, dy) || 0.01;
        const rep = (k * k) / dist;
        dx = (dx / dist) * rep;
        dy = (dy / dist) * rep;
        const di = disp.get(nodes[i].id)!;
        const dj = disp.get(nodes[j].id)!;
        di.x += dx; di.y += dy;
        dj.x -= dx; dj.y -= dy;
      }
    }
    // attraction along edges
    for (const e of edges) {
      const a = pos.get(e.source);
      const b = pos.get(e.target);
      if (!a || !b) continue;
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      const dist = Math.hypot(dx, dy) || 0.01;
      const att = (dist * dist) / k;
      dx = (dx / dist) * att;
      dy = (dy / dist) * att;
      disp.get(e.source)!.x -= dx;
      disp.get(e.source)!.y -= dy;
      disp.get(e.target)!.x += dx;
      disp.get(e.target)!.y += dy;
    }
    // apply, capped by temperature; cool down
    for (const nd of nodes) {
      const d = disp.get(nd.id)!;
      const len = Math.hypot(d.x, d.y) || 0.01;
      const p = pos.get(nd.id)!;
      p.x += (d.x / len) * Math.min(len, temp);
      p.y += (d.y / len) * Math.min(len, temp);
    }
    temp *= 0.97;
  }

  // normalize into the viewBox with padding
  const xs = [...pos.values()].map((p) => p.x);
  const ys = [...pos.values()].map((p) => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 40;
  const sx = (W - 2 * pad) / (maxX - minX || 1);
  const sy = (H - 2 * pad) / (maxY - minY || 1);
  const s = Math.min(sx, sy);
  for (const p of pos.values()) {
    p.x = pad + (p.x - minX) * s;
    p.y = pad + (p.y - minY) * s;
  }
  return pos;
}

export function DependenciesPage() {
  const { data: repos } = useQuery({ queryKey: ["repositories"], queryFn: listRepositories });
  const ready = repos?.filter((r) => r.status === "ready") ?? [];

  const [repoId, setRepoId] = useState("");
  const [hover, setHover] = useState<string | null>(null);
  useEffect(() => {
    if (!repoId && ready.length > 0) setRepoId(String(ready[0].id));
  }, [ready, repoId]);

  const graph = useQuery({
    queryKey: ["graph", repoId],
    queryFn: () => getDependencyGraph(Number(repoId)),
    enabled: !!repoId,
    retry: false,
  });

  const groups = useMemo(
    () => [...new Set((graph.data?.nodes ?? []).map((n) => n.group))],
    [graph.data],
  );
  const color = (g: string) => PALETTE[Math.max(0, groups.indexOf(g)) % PALETTE.length];

  const pos = useMemo(
    () => layout(graph.data?.nodes ?? [], graph.data?.edges ?? []),
    [graph.data],
  );

  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const e of graph.data?.edges ?? []) {
      (m.get(e.source) ?? m.set(e.source, new Set()).get(e.source)!).add(e.target);
      (m.get(e.target) ?? m.set(e.target, new Set()).get(e.target)!).add(e.source);
    }
    return m;
  }, [graph.data]);

  const showLabels = (graph.data?.nodes.length ?? 0) <= 28;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dependencies</h1>
        <p className="text-sm text-muted-foreground">
          Module import graph — which files depend on which, parsed from the source.
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

          {graph.isLoading && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Building dependency graph…
              </div>
              <Skeleton className="h-[420px] w-full rounded-lg" />
            </div>
          )}

          {graph.isError && (
            <p role="alert" className="text-sm text-destructive">
              {graph.error instanceof ApiError ? graph.error.message : "Failed to build graph."}
            </p>
          )}

          {graph.isSuccess && graph.data.nodes.length === 0 && (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No intra-repo import edges found (single-file repo, or an unsupported language).
            </div>
          )}

          {graph.isSuccess && graph.data.nodes.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Network className="size-3.5" />
                  {graph.data.nodes.length} files · {graph.data.edges.length} imports
                </span>
                {graph.data.truncated && <Badge variant="secondary">largest hubs only</Badge>}
                <span className="ml-auto">hover a node to highlight its links</span>
              </div>

              <svg
                viewBox={`0 0 ${W} ${H}`}
                className="w-full rounded-lg border bg-muted/20"
                style={{ maxHeight: 560 }}
              >
                {graph.data.edges.map((e, i) => {
                  const a = pos.get(e.source);
                  const b = pos.get(e.target);
                  if (!a || !b) return null;
                  const active = hover && (e.source === hover || e.target === hover);
                  return (
                    <line
                      key={i}
                      x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                      stroke={active ? "var(--primary)" : "currentColor"}
                      strokeOpacity={hover ? (active ? 0.9 : 0.05) : 0.15}
                      strokeWidth={active ? 1.5 : 1}
                      className="text-muted-foreground"
                    />
                  );
                })}
                {graph.data.nodes.map((nd) => {
                  const p = pos.get(nd.id)!;
                  const r = 4 + Math.min(nd.in_degree, 8) * 1.6;
                  const dim =
                    hover && hover !== nd.id && !neighbors.get(hover)?.has(nd.id);
                  return (
                    <g
                      key={nd.id}
                      transform={`translate(${p.x},${p.y})`}
                      opacity={dim ? 0.2 : 1}
                      onMouseEnter={() => setHover(nd.id)}
                      onMouseLeave={() => setHover(null)}
                      style={{ cursor: "pointer" }}
                    >
                      <circle r={r} fill={color(nd.group)} stroke="white" strokeWidth={0.5} />
                      {(showLabels || hover === nd.id) && (
                        <text
                          x={r + 3}
                          y={3}
                          className="fill-foreground"
                          style={{ fontSize: 9, fontFamily: "monospace" }}
                        >
                          {nd.label}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>

              {groups.length > 1 && (
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                  {groups.map((g) => (
                    <span key={g} className="inline-flex items-center gap-1.5">
                      <span
                        className="inline-block size-2.5 rounded-full"
                        style={{ backgroundColor: color(g) }}
                      />
                      {g || "(root)"}
                    </span>
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
