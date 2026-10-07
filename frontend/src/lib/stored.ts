"use client";

import { useSyncExternalStore } from "react";

const EVENT = "ledgerlens:storage";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(EVENT, onChange);
  };
}

export function getStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function setStored(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage blocked: value is not persisted */
  }
  window.dispatchEvent(new Event(EVENT));
}

/**
 * A localStorage value as React state. Returns `undefined` during server
 * rendering and hydration, then the stored string (or null) on the client.
 */
export function useStored(key: string): string | null | undefined {
  return useSyncExternalStore(
    subscribe,
    () => getStored(key),
    () => undefined,
  );
}
