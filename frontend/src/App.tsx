import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AppLayout } from "@/components/layout/app-layout";
import { RequireAuth } from "@/components/require-auth";
import { LandingPage } from "@/pages/landing";
import { LoginPage } from "@/pages/login";
import { RegisterPage } from "@/pages/register";
import { DashboardPage } from "@/pages/dashboard";

/**
 * Route map.
 *   /             → public landing
 *   /login        → auth
 *   /register     → auth
 *   /app/*        → protected shell (RequireAuth → sidebar layout → feature pages)
 * Feature routes (repositories, search, bugs) mount under /app as they ship.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route element={<RequireAuth />}>
          <Route path="/app" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
