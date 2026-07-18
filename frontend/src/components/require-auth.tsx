/**
 * Route guard for the authenticated app. Redirects to /login when there's no
 * valid session, and preserves the attempted path so we can return after login.
 */

import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/components/auth-provider";
import { getToken } from "@/lib/api";

export function RequireAuth() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // A token exists but /auth/me hasn't resolved yet — avoid flashing the login page.
  if (getToken() && isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
