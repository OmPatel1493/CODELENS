/**
 * Auth state for the whole app.
 *
 * The JWT lives in localStorage (via the api client). This provider exposes the
 * current user and the login/register/logout actions, and uses React Query to
 * load `/auth/me` whenever a token is present. Components read it via `useAuth`.
 */

import { createContext, useContext, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  clearToken,
  getMe,
  getToken,
  loginUser,
  registerUser,
  setToken,
  type AuthUser,
} from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | undefined;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(() => Boolean(getToken()));

  // Only fetch the user when a token exists. `retry: false` so a 401 doesn't loop.
  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: hasToken,
    retry: false,
  });

  async function login(email: string, password: string) {
    const { access_token } = await loginUser(email, password);
    setToken(access_token);
    setHasToken(true);
    await queryClient.invalidateQueries({ queryKey: ["me"] });
  }

  async function register(email: string, password: string) {
    await registerUser(email, password);
    await login(email, password); // auto-login after successful signup
  }

  function logout() {
    clearToken();
    setHasToken(false);
    queryClient.removeQueries({ queryKey: ["me"] });
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading: hasToken && isLoading,
        isAuthenticated: Boolean(user),
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
