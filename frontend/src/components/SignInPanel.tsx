"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { LensMark } from "@/components/LensMark";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { writeSession } from "@/lib/session";

type DemoSession = { tenant_id: string; workspace: string; user: { name: string; role: string } };

export function SignInPanel() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enterDemo() {
    setBusy(true);
    setError(null);
    try {
      const s = await api<DemoSession>("/auth/demo-session");
      writeSession({ tenantId: s.tenant_id, workspace: s.workspace, user: s.user });
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/overview");
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 503
          ? "The demo workspace is still being created. Try again in a few seconds."
          : e instanceof Error
            ? e.message
            : "Sign-in failed.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-[100dvh] grid-cols-1 bg-bg lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Link href="/" className="flex items-center gap-2 self-start">
          <LensMark size={22} />
          <span className="text-[14.5px] font-semibold tracking-tight">Ledger Lens</span>
        </Link>

        <div className="my-auto w-full max-w-[380px] py-16">
          <h1 className="text-[28px] font-semibold leading-tight tracking-tight">Sign in to your workspace</h1>
          <p className="mt-2 text-[14.5px] leading-relaxed text-ink-soft">
            This build runs a demo workspace for a fictional lender, Meridian Capital, with four sample statements from three banks.
          </p>

          <Button size="lg" className="mt-8 w-full" onClick={enterDemo} disabled={busy}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : null}
            Enter demo workspace
            {!busy && <ArrowRight size={16} />}
          </Button>

          {error && (
            <p role="alert" className="mt-3 text-[13px] text-error">
              {error}
            </p>
          )}

          <p className="mt-8 border-t border-line pt-5 text-[13px] leading-relaxed text-muted">
            Single sign-on through Keycloak or Supabase Auth replaces this demo entry in production. Workspaces are isolated by
            tenant at the database layer.
          </p>
        </div>
      </div>

      <div className="relative hidden overflow-hidden border-l border-line bg-surface lg:block">
        <div className="absolute inset-0 flex flex-col justify-center px-14">
          <p className="num text-[13px] text-muted">opening + credits − debits = closing</p>
          <p className="mt-4 max-w-[30ch] text-[30px] font-semibold leading-[1.15] tracking-tight">
            Every number is checked against the statement&apos;s own running balance.
          </p>
          <dl className="mt-10 grid max-w-[420px] grid-cols-2 gap-x-8 gap-y-6 text-[13.5px]">
            {[
              ["Kestrel Bank", "Debit and Credit columns"],
              ["Harbour Trust Bank", "One signed Amount column"],
              ["Oakline MFB", "Amount with a DR/CR flag"],
              ["Your upload", "Any layout, learned once"],
            ].map(([bank, layout]) => (
              <div key={bank} className="border-t border-line pt-3">
                <dt className="font-medium">{bank}</dt>
                <dd className="mt-0.5 text-ink-soft">{layout}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}
