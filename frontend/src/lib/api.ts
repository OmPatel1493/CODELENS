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
  // For FormData, let the browser set Content-Type (it must include the multipart
  // boundary). For everything else we send JSON.
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
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

// ── Repositories ─────────────────────────────────────────────────

export type RepoStatus = "pending" | "indexing" | "ready" | "failed";
export type RepoSource = "github" | "upload";

export interface Repository {
  id: number;
  name: string;
  source: RepoSource;
  status: RepoStatus;
  source_url: string | null;
  file_count: number;
  error_message: string | null;
  created_at: string;
}

export function listRepositories() {
  return apiFetch<Repository[]>("/repositories");
}

export function ingestGithubRepo(url: string) {
  return apiFetch<Repository>("/repositories", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function uploadRepository(name: string, file: File) {
  const form = new FormData();
  form.append("name", name);
  form.append("file", file);
  return apiFetch<Repository>("/repositories/upload", {
    method: "POST",
    body: form,
  });
}

export function deleteRepository(id: number) {
  return apiFetch<void>(`/repositories/${id}`, { method: "DELETE" });
}

export interface RepoStats {
  repositories: number;
  indexed_chunks: number;
  searches_run: number;
}

export function getRepositoryStats() {
  return apiFetch<RepoStats>("/repositories/stats");
}

// ── Semantic search ──────────────────────────────────────────────

export interface SearchHit {
  chunk_id: number;
  file_path: string;
  symbol_name: string | null;
  kind: "file" | "class" | "function";
  start_line: number;
  end_line: number;
  snippet: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchHit[];
}

export function searchRepository(repoId: number, query: string, limit = 8) {
  return apiFetch<SearchResponse>(`/repositories/${repoId}/search`, {
    method: "POST",
    body: JSON.stringify({ query, limit }),
  });
}

// ── Bug localization ─────────────────────────────────────────────

export interface ParsedLog {
  error_type: string | null;
  message: string | null;
  files: string[];
  symbols: string[];
}

export interface LocalizedFile {
  file_path: string;
  score: number;
  reason: string;
  matched_symbols: string[];
  snippet: string;
  start_line: number;
  end_line: number;
}

export interface BugLocalizeResponse {
  parsed: ParsedLog;
  results: LocalizedFile[];
}

export function localizeBug(repoId: number, logText: string, limit = 5) {
  return apiFetch<BugLocalizeResponse>(`/repositories/${repoId}/localize`, {
    method: "POST",
    body: JSON.stringify({ log_text: logText, limit }),
  });
}

// ── Analytics ────────────────────────────────────────────────────

export interface RepoAnalytics {
  kind_breakdown: Record<string, number>;
  language_breakdown: Record<string, number>;
  recent_searches: { query: string; result_count: number; created_at: string }[];
}

export function getRepositoryAnalytics(repoId: number) {
  return apiFetch<RepoAnalytics>(`/repositories/${repoId}/analytics`);
}
