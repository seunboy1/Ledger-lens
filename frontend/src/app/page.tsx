import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import { LensMark } from "@/components/LensMark";
import { MessageView } from "@/components/ask/MessageView";
import { buttonStyles } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { Message } from "@/types/api";

// Real output from the demo workspace (see backend/app/dev/sample_statements.py).
const PREVIEW_ANSWER: Message = {
  id: "preview",
  role: "assistant",
  content: "Total debits (August 2026, 3 banks) came to ₦1,251,582.94 over 25 transactions.",
  route_kind: "sql",
  created_at: "",
  kpis: [
    { label: "Debits", value: "₦1,251,582.94", tone: "debit" },
    { label: "Transactions", value: "25", tone: "neutral" },
  ],
  source_summary: null,
  evidence: null,
  is_helpful: null,
};

const PREVIEW_ROWS = [
  ["21 Aug", "TRF TO ADEBAYO TEXTILE SUPPLIES", "Oakline MFB", "DR", "₦239,700.00"],
  ["10 Aug", "TRF TO ADEBAYO TEXTILE SUPPLIES", "Oakline MFB", "DR", "₦201,600.00"],
  ["11 Aug", "TRF TO OAKLINE MFB BUSINESS ACCT", "Harbour Trust", "-200,000.00", "₦200,000.00"],
  ["27 Aug", "TRF TO HARBOUR TRUST SAVINGS", "Kestrel Bank", "Debit column", "₦150,000.00"],
];

const LABELS = [
  { bank: "Kestrel Bank", printed: "Debit column: 4,400.00", rule: "Separate Debit and Credit columns" },
  { bank: "Harbour Trust Bank", printed: "Amount: -4,400.00", rule: "One signed Amount column" },
  { bank: "Oakline MFB", printed: "4,400.00   DR", rule: "Amount with a DR/CR flag" },
];

const STAGES = [
  {
    title: "Fingerprint the layout",
    body: "Each page's header row and column structure is hashed. Banks on the same core-banking platform share a fingerprint, so the number of layouts stays small.",
  },
  {
    title: "Learn a new layout once",
    body: "On a cache miss, two sample pages produce a strict parsing spec, by LLM or by header heuristics. It is validated on a held-out page, then cached.",
  },
  {
    title: "Parse without a model",
    body: "Every later page with that fingerprint is parsed by plain code. No tokens, no drift, the same output every time.",
  },
  {
    title: "Prove it with the balance",
    body: "Each row must satisfy previous balance plus credit or minus debit. Statements that fail go to a review queue instead of into answers.",
  },
  {
    title: "Answer with SQL",
    body: "Questions become a visible query plan. The database does the arithmetic and returns the exact rows used, which appear beside the answer.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-[100dvh] bg-bg">
      <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-5 md:px-8">
          <Link href="/" className="flex items-center gap-2">
            <LensMark size={22} />
            <span className="text-[15px] font-semibold tracking-tight">Ledger Lens</span>
          </Link>
          <nav aria-label="Primary" className="flex items-center gap-1 sm:gap-2">
            <a href="#how" className="hidden rounded-[var(--radius-ctl)] px-3 py-2 text-[14px] text-ink-soft hover:text-ink sm:block">
              How it works
            </a>
            <a href="#proof" className="hidden rounded-[var(--radius-ctl)] px-3 py-2 text-[14px] text-ink-soft hover:text-ink sm:block">
              The proof
            </a>
            <Link href="/sign-in" className={buttonStyles({ variant: "primary", size: "sm" })}>
              Open the demo
            </Link>
          </nav>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-[1200px] px-5 pb-20 pt-12 md:px-8 lg:pt-16">
          <h1 className="rise-in max-w-[24ch] text-[38px] font-semibold leading-[1.06] tracking-[-0.03em] md:text-[52px] lg:text-[58px]">
            Bank statements you can question, with answers you can check.
          </h1>
          <div className="mt-8 grid items-start gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <div className="rise-in">
            <p className="max-w-[40ch] text-[17px] leading-relaxed text-ink-soft">
              Ledger Lens reads statements from any bank, proves every row against the running balance, and answers in plain language.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/sign-in" className={buttonStyles({ variant: "primary", size: "lg" })}>
                Open the demo <ArrowRight size={16} />
              </Link>
              <a href="#how" className={buttonStyles({ variant: "secondary", size: "lg" })}>
                How it works
              </a>
            </div>
          </div>

          <figure className="rise-in [animation-delay:80ms]">
            <div className="rounded-[var(--radius-panel)] border border-line bg-surface shadow-[var(--shadow-pop)]">
              <div className="space-y-6 p-5 sm:p-6">
                <MessageView
                  message={{ ...PREVIEW_ANSWER, id: "q", role: "user", content: "What were my total debits in August 2026?", kpis: [], route_kind: null }}
                />
                <MessageView message={PREVIEW_ANSWER} />
              </div>
              <div className="border-t border-line">
                <p className="px-5 pt-3 text-[12.5px] text-muted sm:px-6">Largest of the 25 rows behind that total</p>
                <table className="mt-1 w-full table-fixed text-[12.5px]">
                  <caption className="sr-only">Evidence rows for the example answer</caption>
                  <colgroup>
                    <col className="w-[72px] sm:w-[84px]" />
                    <col />
                    <col className="w-[118px] sm:w-[132px]" />
                  </colgroup>
                  <tbody>
                    {PREVIEW_ROWS.map(([date, desc, bank, label, amount]) => (
                      <tr key={date + desc} className="border-t border-line first:border-t-0">
                        <td className="num whitespace-nowrap py-2 pl-5 pr-2 text-muted sm:pl-6">{date}</td>
                        <td className="truncate py-2 pr-2">
                          {desc}
                          <span className="block text-[11.5px] text-muted">
                            {bank}, printed as <span className="num">{label}</span>
                          </span>
                        </td>
                        <td className="num whitespace-nowrap py-2 pl-2 pr-5 text-right text-debit sm:pr-6">−{amount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <figcaption className="mt-3 text-[12.5px] text-muted">Live output from the demo workspace, which runs on fictional statements.</figcaption>
          </figure>
          </div>
        </section>

        {/* Labels */}
        <section className="border-y border-line bg-surface">
          <div className="mx-auto max-w-[1200px] px-5 py-20 md:px-8">
            <h2 className="max-w-[24ch] text-[30px] font-semibold leading-tight tracking-tight">Three banks, three ways to print the same debit.</h2>
            <p className="mt-3 max-w-[60ch] text-[15.5px] leading-relaxed text-ink-soft">
              Labels are normalized once, at ingestion. The bank&apos;s original label stays next to every row as evidence.
            </p>
            <div className="mt-10 overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-[14px]">
                <caption className="sr-only">How each bank layout maps to one canonical row</caption>
                <thead>
                  <tr className="text-left text-[12.5px] text-muted">
                    <th scope="col" className="pb-3 font-normal">Bank</th>
                    <th scope="col" className="pb-3 font-normal">Layout</th>
                    <th scope="col" className="pb-3 font-normal">As printed</th>
                    <th scope="col" className="pb-3 font-normal">Stored as</th>
                  </tr>
                </thead>
                <tbody>
                  {LABELS.map((l) => (
                    <tr key={l.bank} className="border-t border-line">
                      <td className="py-4 pr-4 font-medium">{l.bank}</td>
                      <td className="py-4 pr-4 text-ink-soft">{l.rule}</td>
                      <td className="num py-4 pr-4">{l.printed}</td>
                      <td className="py-4">
                        <span className="num inline-flex items-center gap-2 rounded-full bg-debit-soft px-2.5 py-1 text-[13px] text-debit">
                          debit, ₦4,400.00
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="mx-auto grid max-w-[1200px] scroll-mt-20 gap-12 px-5 py-24 md:px-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <h2 className="text-[30px] font-semibold leading-tight tracking-tight">A model reads two pages per new layout. Code does the rest.</h2>
            <p className="mt-4 max-w-[44ch] text-[15.5px] leading-relaxed text-ink-soft">
              Sending whole statements to an LLM is slow, costs money on every question, and still gets sums wrong. Ledger Lens keeps the model out of the hot path.
            </p>
          </div>
          <ol className="space-y-0">
            {STAGES.map((s) => (
              <li key={s.title} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 border-t border-line py-6 first:border-t-0 first:pt-0">
                <Check size={18} strokeWidth={2} className="mt-1 text-accent" aria-hidden />
                <div>
                  <h3 className="text-[17px] font-semibold tracking-tight">{s.title}</h3>
                  <p className="mt-1.5 max-w-[60ch] text-[15px] leading-relaxed text-ink-soft">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* Proof */}
        <section id="proof" className="scroll-mt-16 bg-sunken">
          <div className="mx-auto max-w-[1200px] px-5 py-24 md:px-8">
            <h2 className="max-w-[26ch] text-[30px] font-semibold leading-tight tracking-tight">
              A statement only counts once its own arithmetic holds.
            </h2>
            <div className="num mt-12 flex flex-wrap items-baseline gap-x-5 gap-y-4 text-[24px] tracking-tight md:text-[34px]">
              <span>₦412,350.18</span>
              <span className="whitespace-nowrap">
                <span className="text-muted">+ </span>
                <span className="text-credit">₦5,170,000.00</span>
              </span>
              <span className="whitespace-nowrap">
                <span className="text-muted">− </span>
                <span className="text-debit">₦2,699,550.00</span>
              </span>
              <span className="whitespace-nowrap">
                <span className="text-muted">= </span>
                <span className="font-medium">₦2,882,800.18</span>
              </span>
            </div>
            <dl className="mt-10 grid max-w-[760px] grid-cols-2 gap-6 text-[14px] sm:grid-cols-4">
              {[
                ["Opening", "printed on page 1"],
                ["Credits", "8 rows, summed in SQL"],
                ["Debits", "112 rows, summed in SQL"],
                ["Closing", "matches the printed figure"],
              ].map(([k, v]) => (
                <div key={k} className="border-t border-line-strong pt-3">
                  <dt className="font-medium">{k}</dt>
                  <dd className="mt-0.5 text-ink-soft">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-10 max-w-[62ch] text-[15px] leading-relaxed text-ink-soft">
              The same check runs row by row. In the demo, one statement has a single misprinted amount. It is held back, the row is flagged with the amount its balance implies, and the statement counts again once a reviewer corrects it.
            </p>
          </div>
        </section>

        {/* Engineering */}
        <section className="mx-auto max-w-[1200px] px-5 py-24 md:px-8">
          <h2 className="text-[30px] font-semibold leading-tight tracking-tight">Built like a production system</h2>
          <div className="mt-10 grid gap-4 md:grid-cols-6">
            <div className="rounded-[var(--radius-panel)] bg-accent-soft p-7 md:col-span-4">
              <p className="num text-[56px] font-medium leading-none tracking-tight text-accent-ink">0</p>
              <p className="mt-4 max-w-[40ch] text-[16px] font-medium">LLM calls to parse a statement whose layout has been seen before.</p>
              <p className="mt-2 max-w-[52ch] text-[14.5px] leading-relaxed text-ink-soft">
                Specs are cached by layout fingerprint. A second Kestrel Bank statement reuses the first one&apos;s spec and parses with plain code.
              </p>
            </div>
            <div className="rounded-[var(--radius-panel)] border border-line bg-surface p-7 md:col-span-2">
              <p className="text-[16px] font-medium">Isolation in the database</p>
              <p className="mt-2 text-[14.5px] leading-relaxed text-ink-soft">
                Postgres row-level security scopes every query to the caller&apos;s tenant, so a routing bug cannot leak another lender&apos;s data.
              </p>
            </div>
            <div className="rounded-[var(--radius-panel)] border border-line bg-surface p-7 md:col-span-2">
              <p className="text-[16px] font-medium">Open-source stack</p>
              <ul className="num mt-3 space-y-1.5 text-[13.5px] text-ink-soft">
                <li>Next.js, FastAPI</li>
                <li>Postgres + pgvector</li>
                <li>Prefect, RabbitMQ, MinIO</li>
                <li>pdfplumber, open-weight LLMs</li>
              </ul>
            </div>
            <div className="rounded-[var(--radius-panel)] border border-line bg-ink p-7 text-bg md:col-span-4">
              <p className="text-[16px] font-medium">Tested against ground truth, not against itself</p>
              <p className="mt-2 max-w-[56ch] text-[14.5px] leading-relaxed opacity-75">
                End-to-end tests render statements to PDF, push them through the real pipeline, ask questions over HTTP, and compare every figure with totals computed independently from the source data.
              </p>
              <pre className="num mt-5 overflow-x-auto rounded-[var(--radius-ctl)] bg-bg/10 p-4 text-[12.5px] leading-relaxed">
                {`assert ngn(answer)[0] == month_total(VERIFIED, 2026, 8, debits)
assert detail["proof"]["document_check_ok"] is True
assert layout["times_reused"] >= 2   # no new induction`}
              </pre>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-5 py-8 text-[13.5px] text-muted md:px-8">
          <p className="flex items-center gap-2">
            <LensMark size={18} /> Ledger Lens, designed and built by Oluwaseun Adeyo.
          </p>
          <Link href="/sign-in" className={cn("text-ink-soft hover:text-ink")}>
            Open the demo
          </Link>
        </div>
      </footer>
    </div>
  );
}
