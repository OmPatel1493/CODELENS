/**
 * Central API client.
 *
 * Every network call goes through `apiFetch` so we have ONE place that knows the
 * base URL, sets JSON headers, and turns non-2xx responses into thrown errors
 * (which React Query then surfaces as `error` state). No component ever calls
 * `fetch` directly.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// ── Typed endpoints ──────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
}

export function getHealth() {
  return apiFetch<HealthResponse>("/health");
}
