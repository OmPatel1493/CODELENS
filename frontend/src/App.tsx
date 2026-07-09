import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AppLayout } from "@/components/layout/app-layout";
import { LandingPage } from "@/pages/landing";
import { LoginPage } from "@/pages/login";
import { DashboardPage } from "@/pages/dashboard";

/**
 * Route map.
 *   /            → public landing
 *   /login       → auth
 *   /app/*       → authenticated shell (sidebar) with nested feature pages
 * Feature routes (repositories, search, bugs) mount here as they ship.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
