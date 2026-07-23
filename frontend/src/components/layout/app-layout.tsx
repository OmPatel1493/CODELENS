/**
 * Authenticated app shell: fixed sidebar (nav) + top bar + routed content area.
 * Nested routes render into <Outlet />.
 */

import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  Sparkles,
  FolderGit2,
  Bug,
  ScanSearch,
  LogOut,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";
import { BackendStatus } from "@/components/backend-status";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/repositories", label: "Repositories", icon: FolderGit2 },
  { to: "/app/search", label: "Search", icon: Search },
  { to: "/app/ask", label: "Ask", icon: Sparkles },
  { to: "/app/bugs", label: "Bug Localization", icon: Bug },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  return (
    <div className="flex min-h-svh bg-background text-foreground">
      {/* Sidebar */}
      <aside className="hidden w-60 flex-col border-r bg-sidebar md:flex">
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <ScanSearch className="size-5 text-primary" />
          <span className="font-semibold tracking-tight">CodeLens</span>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="space-y-3 border-t p-3">
          {user && (
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-xs text-muted-foreground" title={user.email}>
                {user.email}
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={logout}
                aria-label="Sign out"
              >
                <LogOut className="size-4" />
              </Button>
            </div>
          )}
          <BackendStatus />
        </div>
      </aside>

      {/* Main column */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b px-6">
          <span className="text-sm text-muted-foreground md:hidden">
            CodeLens
          </span>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
