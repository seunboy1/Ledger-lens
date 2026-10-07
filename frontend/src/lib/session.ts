"use client";

import { getStored, setStored } from "@/lib/stored";
import type { Session } from "@/types/api";

export const SESSION_KEY = "ledgerlens.session";

export function parseSession(raw: string | null | undefined): Session | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function readSession(): Session | null {
  return parseSession(getStored(SESSION_KEY));
}

export function writeSession(session: Session) {
  setStored(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  setStored(SESSION_KEY, null);
}
