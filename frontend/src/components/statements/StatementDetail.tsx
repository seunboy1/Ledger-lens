"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Check, X } from "lucide-react";
import { ErrorState, SkeletonRows } from "@/components/States";
import { StatusBadge } from "@/components/StatusBadge";
import { BalanceProof } from "@/components/statements/BalanceProof";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/useApi";
import { api, ApiError } from "@/lib/api";
import { dateRange, naira, shortDate } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { DocumentDetail, Txn } from "@/types/api";

const PAGE = 50;

const CONVENTIONS: Record<string, string> = {
  separate_debit_credit_columns: "Separate Debit and Credit columns",
  single_signed_amount: "One signed Amount column",
  single_amount_with_flag: "Amount with a DR/CR flag",
};

/** The amount the printed balances imply for a row that failed the check. */
function impliedAmount(t: Txn): { amount: number; type: "credit" | "debit" } | null {
  if (t.expected_balance === null || t.balance_after === null) return null;
  const signed = t.type === "credit" ? t.amount : -t.amount;
  const previous = t.expected_balance - signed;
  const delta = Math.round((t.balance_after - previous) * 100) / 100;
  if (delta === 0) return null;
  return { amount: Math.abs(delta), type: delta > 0 ? "credit" : "debit" };
}

export function StatementDetail({ id }: { id: string }) {
  const { data: doc, error, loading, refresh, setData } = useApi<DocumentDetail>(`/documents/${id}`, {
    pollMs: false,
  });
  const [page, setPage] = useState(0);
  const rows = useApi<{ total: number; items: Txn[] }>(`/documents/${id}/transactions?limit=${PAGE}&offset=${page * PAGE}`);

  if (error) {
    return (
      <Shell>
        <ErrorState message={error.status === 404 ? "This statement does not exist in this workspace." : error.message} onRetry={() => void refresh()} />
      </Shell>
    );
  }
  if (loading || !doc) {
    return (
      <Shell>
        <div className="skeleton mb-6 h-8 w-64" />
        <SkeletonRows rows={6} />
      </Shell>
    );
  }

  const p = doc.proof;
  const processing = doc.status === "processing" || doc.status === "uploaded";

  async function decide(action: "accept" | "reject") {
    try {
      const updated = await api<DocumentDetail>(`/documents/${id}/review`, { method: "POST", body: { action } });
      setData(updated);
      void rows.refresh();
      toast.success(action === "accept" ? "Statement accepted" : "Statement rejected");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Review failed");
    }
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[24px] font-semibold tracking-tight">{doc.bank_name ?? "Statement"}</h1>
          <p className="mt-1 truncate text-[13.5px] text-ink-soft">
            {doc.filename}
            {doc.page_count ? `, ${doc.page_count} page${doc.page_count > 1 ? "s" : ""}` : ""}
            {doc.period_start ? `, ${dateRange(doc.period_start, doc.period_end)}` : ""}
          </p>
        </div>
        <StatusBadge status={doc.status} className="text-[13px]" />
      </div>

      {doc.error && doc.status !== "reconciled" && <p className="mt-4 text-[13.5px] text-error">{doc.error}</p>}

      {processing ? (
        <ProcessingNote doc={doc} onRefresh={() => void refresh()} />
      ) : (
        <>
          <BalanceProof proof={p} className="mt-8" />

          {doc.failing_rows.length > 0 && (
            <ReviewQueue doc={doc} onUpdated={(d) => {
              setData(d);
              void rows.refresh();
            }} />
          )}

          {doc.status === "needs_review" && (
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" onClick={() => void decide("accept")} disabled={doc.failing_rows.some((r) => !r.reconciled)}>
                Accept statement
              </Button>
              <Button variant="danger" onClick={() => void decide("reject")}>
                Reject statement
              </Button>
            </div>
          )}

          {doc.layout && (
            <section aria-labelledby="layout-h" className="mt-10">
              <h2 id="layout-h" className="text-[14px] font-semibold">Layout</h2>
              <dl className="mt-3 grid grid-cols-2 gap-x-8 gap-y-4 text-[13.5px] md:grid-cols-4">
                <Fact label="Amount convention" value={CONVENTIONS[doc.layout.amount_convention ?? ""] ?? doc.layout.amount_convention ?? "n/a"} />
                <Fact label="Date format" value={doc.layout.date_format ?? "n/a"} mono />
                <Fact
                  label="Spec learned by"
                  value={doc.layout.induced_by === "heuristic" ? "Header heuristics (no LLM call)" : "LLM, from 2 sample pages"}
                />
                <Fact label="Reused" value={`${doc.layout.times_reused} time${doc.layout.times_reused === 1 ? "" : "s"}, fingerprint ${doc.layout.fingerprint}`} mono />
              </dl>
            </section>
          )}

          <section aria-labelledby="rows-h" className="mt-10">
            <div className="flex items-baseline justify-between">
              <h2 id="rows-h" className="text-[14px] font-semibold">Transactions</h2>
              {rows.data && <p className="num text-[13px] text-muted">{rows.data.total.toLocaleString()} rows</p>}
            </div>
            <div className="mt-3 overflow-x-auto rounded-[var(--radius-panel)] border border-line bg-surface">
              {rows.loading && !rows.data ? (
                <div className="p-4">
                  <SkeletonRows rows={5} />
                </div>
              ) : (
                <table className="w-full min-w-[760px] border-collapse text-[13px]">
                  <caption className="sr-only">Extracted transactions in statement order</caption>
                  <thead>
                    <tr className="text-left text-[12.5px] text-muted">
                      <th scope="col" className="px-4 py-2.5 font-normal">Date</th>
                      <th scope="col" className="px-4 py-2.5 font-normal">Narration</th>
                      <th scope="col" className="px-4 py-2.5 font-normal">Label</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-normal">Amount</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-normal">Balance</th>
                      <th scope="col" className="px-4 py-2.5 font-normal">Check</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.data?.items.map((t) => (
                      <tr key={t.id} className={cn("border-t border-line", !t.reconciled && "bg-error-soft")}>
                        <td className="num whitespace-nowrap px-4 py-2 text-ink-soft">{shortDate(t.date)}</td>
                        <td className="max-w-[340px] truncate px-4 py-2" title={t.description}>{t.description}</td>
                        <td className="num px-4 py-2 text-muted">{t.raw_label}</td>
                        <td className={cn("num whitespace-nowrap px-4 py-2 text-right", t.type === "credit" ? "text-credit" : "text-debit")}>
                          {naira(t.type === "credit" ? t.amount : -t.amount, { signed: true })}
                        </td>
                        <td className="num whitespace-nowrap px-4 py-2 text-right">{naira(t.balance_after)}</td>
                        <td className="whitespace-nowrap px-4 py-2 text-[12.5px]">
                          {t.reconciled ? (
                            <span className="inline-flex items-center gap-1 text-credit">
                              <Check size={13} aria-hidden /> {t.repair_source === "human" ? "Corrected" : "Reconciles"}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-error">
                              <X size={13} aria-hidden /> Off
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            {rows.data && rows.data.total > PAGE && (
              <div className="mt-3 flex items-center justify-end gap-2 text-[13px]">
                <span className="num text-muted">
                  {page * PAGE + 1} to {Math.min((page + 1) * PAGE, rows.data.total)} of {rows.data.total}
                </span>
                <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage((n) => n - 1)}>
                  Previous
                </Button>
                <Button variant="secondary" size="sm" disabled={(page + 1) * PAGE >= rows.data.total} onClick={() => setPage((n) => n + 1)}>
                  Next
                </Button>
              </div>
            )}
          </section>
        </>
      )}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-[1080px] px-5 py-8 md:px-8">
      <Link href="/statements" className="mb-6 inline-flex items-center gap-1.5 text-[13px] text-ink-soft hover:text-ink">
        <ArrowLeft size={14} aria-hidden /> Statements
      </Link>
      {children}
    </div>
  );
}

function Fact({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="border-t border-line pt-2.5">
      <dt className="text-[12.5px] text-muted">{label}</dt>
      <dd className={cn("mt-0.5", mono && "num text-[13px]")}>{value}</dd>
    </div>
  );
}

function ProcessingNote({ doc, onRefresh }: { doc: DocumentDetail; onRefresh: () => void }) {
  return (
    <div className="mt-8 rounded-[var(--radius-panel)] border border-line bg-surface px-5 py-5">
      <p className="text-[14px] font-medium">Extracting and reconciling</p>
      <p className="num mt-1 text-[13px] text-ink-soft">
        {doc.chunks.done} of {Math.max(doc.chunks.total, 1)} page chunks done
      </p>
      <Button variant="secondary" size="sm" className="mt-4" onClick={onRefresh}>
        Refresh
      </Button>
    </div>
  );
}

function ReviewQueue({ doc, onUpdated }: { doc: DocumentDetail; onUpdated: (d: DocumentDetail) => void }) {
  return (
    <section aria-labelledby="review-h" className="mt-6 rounded-[var(--radius-panel)] border border-warn/40 bg-surface">
      <div className="border-b border-line px-5 py-3.5">
        <h2 id="review-h" className="text-[14px] font-semibold">
          {doc.failing_rows.length} row{doc.failing_rows.length > 1 ? "s" : ""} to review
        </h2>
        <p className="mt-0.5 text-[13px] text-ink-soft">
          The printed running balance does not match these amounts. Correct the row and the whole statement is re-checked.
        </p>
      </div>
      <ul>
        {doc.failing_rows.map((t) => (
          <ReviewRow key={t.id} txn={t} onUpdated={onUpdated} />
        ))}
      </ul>
    </section>
  );
}

function ReviewRow({ txn, onUpdated }: { txn: Txn; onUpdated: (d: DocumentDetail) => void }) {
  const implied = impliedAmount(txn);
  const [value, setValue] = useState(implied ? implied.amount.toFixed(2) : txn.amount.toFixed(2));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    const amount = Number(value.replace(/,/g, ""));
    if (!Number.isFinite(amount) || amount <= 0) {
      setErr("Enter an amount greater than zero");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      const updated = await api<DocumentDetail>(`/transactions/${txn.id}`, {
        method: "PATCH",
        body: { amount, ...(implied && implied.type !== txn.type ? { transaction_type: implied.type } : {}) },
      });
      onUpdated(updated);
      toast.success(updated.status === "reconciled" ? "Statement now reconciles" : "Row updated, still not reconciling");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  const inputId = `amount-${txn.id}`;
  return (
    <li className="grid gap-4 border-t border-line px-5 py-4 first:border-t-0 md:grid-cols-[1fr_auto] md:items-end">
      <div className="min-w-0">
        <p className="text-[13.5px] font-medium">{txn.description}</p>
        <p className="num mt-0.5 text-[12.5px] text-muted">
          {shortDate(txn.date)}, page {txn.page_number ?? "?"}
        </p>
        <dl className="mt-3 grid grid-cols-3 gap-4 text-[13px]">
          <div>
            <dt className="text-muted">Extracted amount</dt>
            <dd className="num mt-0.5">{naira(txn.amount)}</dd>
          </div>
          <div>
            <dt className="text-muted">Printed balance</dt>
            <dd className="num mt-0.5">{naira(txn.balance_after)}</dd>
          </div>
          <div>
            <dt className="text-muted">Balance implies</dt>
            <dd className="num mt-0.5 font-medium text-accent-ink">{implied ? naira(implied.amount) : "n/a"}</dd>
          </div>
        </dl>
      </div>
      <form
        className="flex flex-col gap-1.5"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <label htmlFor={inputId} className="text-[12.5px] text-ink-soft">
          Corrected amount (₦)
        </label>
        <div className="flex gap-2">
          <input
            id={inputId}
            inputMode="decimal"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-invalid={Boolean(err)}
            aria-describedby={err ? `${inputId}-err` : undefined}
            className="num h-9 w-36 rounded-[var(--radius-ctl)] border border-line-strong bg-bg px-2.5 text-right text-[14px] outline-none focus:border-accent focus:[box-shadow:var(--focus-ring)]"
          />
          <Button type="submit" disabled={saving}>
            {saving ? "Checking" : "Save and re-check"}
          </Button>
        </div>
        {err && (
          <p id={`${inputId}-err`} className="text-[12.5px] text-error">
            {err}
          </p>
        )}
      </form>
    </li>
  );
}
