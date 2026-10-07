"use client";

import { readSession } from "@/lib/session";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Options = Omit<RequestInit, "body"> & { body?: unknown; raw?: BodyInit };

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const session = readSession();
  const headers = new Headers(opts.headers);
  if (session) headers.set("X-Tenant-Id", session.tenantId);
  let body: BodyInit | undefined = opts.raw;
  if (opts.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(path.startsWith("http") ? path : `${API_URL}${path}`, { ...opts, headers, body });
  } catch {
    throw new ApiError(0, "Can't reach the Ledger Lens API. Is the backend running on port 8000?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
