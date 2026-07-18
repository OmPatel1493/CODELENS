/**
 * Central API client.
 *
 * Every network call goes through `apiFetch` so we have ONE place that knows the
 * base URL, sets JSON headers, attaches the auth token, and turns non-2xx
 * responses into thrown errors (which React Query surfaces as `error` state).
 * No component ever calls `fetch` directly.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

const TOKEN_KEY = "codelens-token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Best-effort extraction of a human message from FastAPI's error body. */
async function extractError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg;
    }
  } catch {
    /* non-JSON body */
  }
  return `Request failed: ${response.status}`;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await extractError(response));
  }

  // 204 No Content and empty bodies would break response.json().
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// ── Types ────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
}

export interface AuthUser {
  id: number;
  email: string;
  created_at: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ── Endpoints ────────────────────────────────────────────────────

export function getHealth() {
  return apiFetch<HealthResponse>("/health");
}

export function registerUser(email: string, password: string) {
  return apiFetch<AuthUser>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function loginUser(email: string, password: string) {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe() {
  return apiFetch<AuthUser>("/auth/me");
}
