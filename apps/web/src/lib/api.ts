import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { SessionUser } from "@/lib/types";

export const SESSION_COOKIE = "oportuna_session";

const INTERNAL_API =
  process.env.OPORTUNA_INTERNAL_API_URL ??
  process.env.API_INTERNAL_URL ??
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiGet<T>(path: string, token?: string | null): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${INTERNAL_API}/api${path}`, {
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, "No se pudo contactar con la API de Oportuna.");
  }
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      /* keep default */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export async function apiSend<T>(
  path: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  body?: unknown,
  token?: string | null,
): Promise<T> {
  const response = await fetch(`${INTERNAL_API}/api${path}`, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const payload = await response.json();
      detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    } catch {
      /* keep default */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export async function getSessionToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? null;
}

export const getSessionUser = cache(async (): Promise<SessionUser | null> => {
  const token = await getSessionToken();
  if (!token) return null;
  try {
    const payload = await apiGet<{ user: SessionUser | null }>("/auth/me", token);
    return payload.user;
  } catch {
    return null;
  }
});

export async function requireUser(nextPath = "/"): Promise<SessionUser> {
  const user = await getSessionUser();
  if (!user) {
    redirect(`/entrar?next=${encodeURIComponent(nextPath)}`);
  }
  return user;
}

export async function requireAdmin(): Promise<SessionUser> {
  const user = await requireUser("/admin");
  if (user.role !== "admin") {
    redirect("/");
  }
  return user;
}
