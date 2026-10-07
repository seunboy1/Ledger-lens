"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { FileText, LayoutGrid, LogOut, Menu, MessageSquareText, X } from "lucide-react";
import { LensMark } from "@/components/LensMark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useApi } from "@/hooks/useApi";
import { clearSession, parseSession, SESSION_KEY } from "@/lib/session";
import { useStored } from "@/lib/stored";
import { cn } from "@/lib/cn";
import type { Workspace } from "@/types/api";

const NAV = [
  { href: "/overview", label: "Overview", Icon: LayoutGrid },
  { href: "/ask", label: "Ask", Icon: MessageSquareText },
  { href: "/statements", label: "Statements", Icon: FileText },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const raw = useStored(SESSION_KEY);
  const session = useMemo(() => parseSession(raw), [raw]);
  const ready = raw !== undefined && session !== null;
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    if (raw !== undefined && !session) router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
  }, [raw, session, router, pathname]);

  const { data: ws } = useApi<Workspace>(ready ? "/workspace" : null, { pollMs: 15000 });
  const review = ws?.documents.needs_review ?? 0;

  if (!ready || !session) {
    return <div className="min-h-[100dvh] bg-bg" aria-busy="true" />;
  }

  function signOut() {
    clearSession();
    router.replace("/sign-in");
  }

  const nav = (
    <nav aria-label="Workspace" className="flex flex-col gap-0.5">
      {NAV.map(({ href, label, Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={() => setDrawer(false)}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex h-9 items-center gap-2.5 rounded-[var(--radius-ctl)] px-2.5 text-[13.5px] transition-colors",
              active ? "bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--border)]" : "text-ink-soft hover:bg-sunken hover:text-ink",
            )}
          >
            <Icon size={16} strokeWidth={1.75} aria-hidden />
            {label}
            {href === "/statements" && review > 0 && (
              <span className="num ml-auto rounded-full bg-warn-soft px-1.5 text-[11.5px] font-medium text-warn" aria-label={`${review} need review`}>
                {review}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );

  const sidebar = (
    <div className="flex h-full flex-col gap-6 px-3 py-4">
      <Link href="/" className="flex items-center gap-2 px-1.5">
        <LensMark size={22} />
        <span className="text-[14.5px] font-semibold tracking-tight">Ledger Lens</span>
      </Link>

      <div className="px-1.5">
        <p className="text-[12px] text-muted">Workspace</p>
        <p className="truncate text-[13.5px] font-medium">{ws?.tenant.name ?? session.workspace}</p>
        <p className="num mt-0.5 text-[12px] text-muted">
          {ws ? `${ws.banks.length} banks, ${ws.verified_transactions.toLocaleString()} verified rows` : "Loading"}
        </p>
      </div>

      {nav}

      <div className="mt-auto space-y-3 border-t border-line px-1.5 pt-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="truncate text-[13px] font-medium">{session.user.name}</p>
            <p className="text-[12px] text-muted">{session.user.role}</p>
          </div>
          <button
            type="button"
            onClick={signOut}
            aria-label="Sign out"
            title="Sign out"
            className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-ctl)] text-muted hover:bg-sunken hover:text-ink"
          >
            <LogOut size={15} strokeWidth={1.75} />
          </button>
        </div>
        <ThemeToggle />
      </div>
    </div>
  );

  return (
    <div className="flex min-h-[100dvh] bg-bg">
      <aside className="sticky top-0 hidden h-[100dvh] w-60 shrink-0 border-r border-line bg-bg md:block">{sidebar}</aside>

      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-ink/30" onClick={() => setDrawer(false)} />
          <div className="rise-in absolute inset-y-0 left-0 w-72 border-r border-line bg-bg">{sidebar}</div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-12 items-center gap-3 border-b border-line bg-bg/90 px-4 backdrop-blur md:hidden">
          <button type="button" aria-label="Open navigation" onClick={() => setDrawer(true)} className="-ml-1 flex h-8 w-8 items-center justify-center rounded-[var(--radius-ctl)] hover:bg-sunken">
            {drawer ? <X size={18} /> : <Menu size={18} />}
          </button>
          <LensMark size={20} />
          <span className="text-[14px] font-semibold">Ledger Lens</span>
        </header>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
