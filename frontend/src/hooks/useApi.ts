"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";

type State<T> = { key: string | null; data: T | null; error: ApiError | null };

/** Fetch-on-mount with refresh and optional polling. Results are keyed by path. */
export function useApi<T>(path: string | null, opts: { pollMs?: number | false } = {}) {
  const [state, setState] = useState<State<T>>({ key: null, data: null, error: null });
  const alive = useRef(true);

  const settle = useCallback(
    (p: string, result: Promise<T>) =>
      result.then(
        (data) => {
          if (alive.current) setState({ key: p, data, error: null });
        },
        (e: unknown) => {
          const error = e instanceof ApiError ? e : new ApiError(0, String(e));
          if (alive.current) setState((s) => ({ key: p, data: s.key === p ? s.data : null, error }));
        },
      ),
    [],
  );

  const load = useCallback(async () => {
    if (path) await settle(path, api<T>(path));
  }, [path, settle]);

  useEffect(() => {
    alive.current = true;
    if (path) void settle(path, api<T>(path));
    return () => {
      alive.current = false;
    };
  }, [path, settle]);

  useEffect(() => {
    if (!opts.pollMs || !path) return;
    const id = window.setInterval(() => void load(), opts.pollMs);
    return () => window.clearInterval(id);
  }, [load, opts.pollMs, path]);

  const current = state.key === path;
  const setData = useCallback((data: T) => setState({ key: path, data, error: null }), [path]);

  return {
    data: current ? state.data : null,
    error: current ? state.error : null,
    loading: path !== null && !current,
    refresh: load,
    setData,
  };
}
