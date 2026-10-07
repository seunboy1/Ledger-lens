"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type DragEvent } from "react";
import { toast } from "sonner";
import { ChevronRight, FileUp } from "lucide-react";
import { ErrorState, SkeletonRows } from "@/components/States";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/useApi";
import { API_URL, api } from "@/lib/api";
import { dateRange, percent } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { DocumentSummary } from "@/types/api";

type UploadTarget = { document_id: string; upload_url: string };
type LocalUpload = { name: string; state: "uploading" | "queued" | "error"; error?: string };

const MAX_BYTES = 25 * 1024 * 1024;

// A fourth bank layout the demo has not seen, so its spec is learned live.
const SAMPLE = {
  path: "/samples/palmgrove-bank-current-jul-sep-2026.pdf",
  name: "palmgrove-bank-current-jul-sep-2026.pdf",
};

export function StatementsView() {
  const [uploads, setUploads] = useState<LocalUpload[]>([]);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const { data, error, loading, refresh } = useApi<DocumentSummary[]>("/documents");
  const busy = (data ?? []).some((d) => d.status === "processing" || d.status === "uploaded");

  // Poll only while something is still being extracted.
  useEffect(() => {
    if (!busy) return;
    const id = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(id);
  }, [busy, refresh]);

  async function uploadOne(file: File) {
    const set = (patch: Partial<LocalUpload>) =>
      setUploads((prev) => prev.map((u) => (u.name === file.name ? { ...u, ...patch } : u)));
    setUploads((prev) => [...prev.filter((u) => u.name !== file.name), { name: file.name, state: "uploading" }]);

    if (file.type && file.type !== "application/pdf") return set({ state: "error", error: "Only PDF statements are supported" });
    if (file.size > MAX_BYTES) return set({ state: "error", error: "Larger than 25 MB" });

    try {
      const target = await api<UploadTarget>("/documents/upload", { method: "POST", body: { filename: file.name } });
      if (target.upload_url.startsWith(API_URL)) {
        await api(target.upload_url, { method: "PUT", raw: file, headers: { "Content-Type": "application/pdf" } });
      } else {
        const res = await fetch(target.upload_url, { method: "PUT", body: file });
        if (!res.ok) throw new Error(`Storage rejected the upload (${res.status})`);
      }
      await api(`/documents/${target.document_id}/notify-uploaded`, { method: "POST" });
      set({ state: "queued" });
      void refresh();
      window.setTimeout(() => setUploads((prev) => prev.filter((u) => u.name !== file.name)), 1500);
    } catch (e) {
      set({ state: "error", error: e instanceof Error ? e.message : "Upload failed" });
      toast.error(`${file.name}: upload failed`);
    }
  }

  async function trySample() {
    try {
      const res = await fetch(SAMPLE.path);
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      await uploadOne(new File([blob], SAMPLE.name, { type: "application/pdf" }));
    } catch {
      toast.error("The sample statement could not be loaded");
    }
  }

  function onFiles(files: FileList | null) {
    if (!files?.length) return;
    Array.from(files).forEach((f) => void uploadOne(f));
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    onFiles(e.dataTransfer.files);
  }

  const review = (data ?? []).filter((d) => d.status === "needs_review");

  return (
    <div className="mx-auto max-w-[1080px] px-5 py-8 md:px-8">
      <h1 className="text-[24px] font-semibold tracking-tight">Statements</h1>
      <p className="mt-1 max-w-[62ch] text-[14.5px] leading-relaxed text-ink-soft">
        Statements are parsed, then every row is checked against the printed running balance. Only statements that reconcile feed answers and the overview.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "mt-7 flex flex-col items-start gap-4 rounded-[var(--radius-panel)] border border-dashed px-5 py-5 transition-colors sm:flex-row sm:items-center",
          dragging ? "border-accent bg-accent-soft" : "border-line-strong bg-surface",
        )}
      >
        <FileUp size={20} strokeWidth={1.5} className="shrink-0 text-ink-soft" aria-hidden />
        <div className="flex-1">
          <p className="text-[14px] font-medium">Drop PDF statements here</p>
          <p className="text-[13px] text-ink-soft">Any bank, any length, up to 25 MB each. New layouts are learned on first sight.</p>
        </div>
        <input ref={input} type="file" accept="application/pdf,.pdf" multiple className="sr-only" id="statement-files" onChange={(e) => {
          onFiles(e.target.files);
          e.target.value = "";
        }} />
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={() => void trySample()} title="Uploads a sample Palmgrove Bank statement in a layout the demo has not seen yet">
            Try a sample
          </Button>
          <Button variant="secondary" onClick={() => input.current?.click()}>
            Choose files
          </Button>
        </div>
      </div>

      {uploads.length > 0 && (
        <ul className="mt-3 space-y-1.5" aria-live="polite">
          {uploads.map((u) => (
            <li key={u.name} className="flex items-center justify-between gap-3 text-[13px]">
              <span className="truncate">{u.name}</span>
              <span className={cn(u.state === "error" ? "text-error" : "text-muted")}>
                {u.state === "uploading" ? "Uploading" : u.state === "queued" ? "Queued for extraction" : u.error}
              </span>
            </li>
          ))}
        </ul>
      )}

      {review.length > 0 && (
        <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[var(--radius-panel)] bg-warn-soft px-4 py-3 text-[13.5px] text-warn">
          <span className="font-medium">
            {review.length} statement{review.length > 1 ? "s" : ""} need{review.length === 1 ? "s" : ""} review.
          </span>
          <span>Rows that don&apos;t reconcile are held back from answers until they are corrected.</span>
        </div>
      )}

      <section className="mt-8" aria-label="Statement list">
        {error ? (
          <ErrorState message={error.message} onRetry={() => void refresh()} />
        ) : loading && !data ? (
          <SkeletonRows rows={4} />
        ) : !data?.length ? (
          <p className="py-10 text-center text-[14px] text-muted">No statements yet. Upload one to get started.</p>
        ) : (
          <div className="overflow-x-auto rounded-[var(--radius-panel)] border border-line bg-surface">
            <table className="w-full min-w-[660px] border-collapse text-[13.5px]">
              <caption className="sr-only">Uploaded statements</caption>
              <thead>
                <tr className="text-left text-[12.5px] text-muted">
                  <th scope="col" className="px-4 py-2.5 font-normal">Statement</th>
                  <th scope="col" className="px-4 py-2.5 font-normal">Period</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-normal">Rows</th>
                  <th scope="col" className="px-4 py-2.5 text-right font-normal">Verified</th>
                  <th scope="col" className="px-4 py-2.5 font-normal">Status</th>
                  <th scope="col" className="w-8 px-2 py-2.5"><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody>
                {data.map((d) => (
                  <tr key={d.id} className="group border-t border-line transition-colors hover:bg-sunken">
                    <td className="px-4 py-3">
                      <Link href={`/statements/${d.id}`} className="block rounded-sm">
                        <span className="font-medium">{d.bank_name ?? (d.status === "processing" || d.status === "uploaded" ? "Detecting bank" : "Unknown bank")}</span>
                        <span className="block max-w-[34ch] truncate text-[12.5px] text-muted">{d.filename}</span>
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-ink-soft">
                      {dateRange(d.period_start, d.period_end)}
                    </td>
                    <td className="num px-4 py-3 text-right">{d.transaction_count.toLocaleString()}</td>
                    <td className="num px-4 py-3 text-right">{percent(d.reconciliation_score, d.reconciliation_score === 1 ? 0 : 1)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="px-2 py-3 text-muted">
                      <Link href={`/statements/${d.id}`} aria-label={`Open ${d.filename}`} tabIndex={-1}>
                        <ChevronRight size={16} className="transition-transform group-hover:translate-x-0.5" aria-hidden />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
