const configuredApiUrl =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
const parsedApiUrl = new URL(configuredApiUrl);
const API_URL = `${parsedApiUrl.origin}${parsedApiUrl.pathname.replace(/\/+$/, "")}`;

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(new URL(`${API_URL}${path}`), { ...init, headers });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String(payload.detail)
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}
