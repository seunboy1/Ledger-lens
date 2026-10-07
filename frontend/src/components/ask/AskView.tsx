"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { toast } from "sonner";
import { MoreHorizontal, PanelRightOpen, Plus, X } from "lucide-react";
import { Composer } from "@/components/ask/Composer";
import { EvidencePanel } from "@/components/ask/EvidencePanel";
import { MessageView } from "@/components/ask/MessageView";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/States";
import { api, ApiError } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { Conversation, Evidence, Message, SendResult } from "@/types/api";

const SUGGESTIONS = [
  "What were my total debits in August 2026?",
  "What was my net cashflow in July 2026?",
  "Which of my payments look like subscriptions?",
  "Show my top 5 largest debits",
  "What was my balance at the end of September 2026?",
  "Any loan repayments to other lenders?",
];

export function AskView() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [evidence, setEvidence] = useState<{ messageId: string; evidence: Evidence } | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const threadEnd = useRef<HTMLDivElement>(null);
  const autoAsked = useRef(false);

  const loadConversations = useCallback(async () => {
    try {
      const list = await api<Conversation[]>("/conversations");
      setConversations(list);
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const openConversation = useCallback(async (id: string) => {
    setActiveId(id);
    setMessages([]);
    setEvidence(null);
    try {
      const list = await api<Message[]>(`/conversations/${id}/messages`);
      setMessages(list);
      const last = [...list].reverse().find((m) => m.evidence && m.evidence.rows.length);
      setEvidence(last?.evidence ? { messageId: last.id, evidence: last.evidence } : null);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not load the conversation");
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    api<Conversation[]>("/conversations").then(
      (list) => {
        if (!ignore) setConversations(list);
      },
      (e: unknown) => {
        if (!ignore) setLoadError(e instanceof Error ? e.message : String(e));
      },
    );
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  const send = useCallback(
    async (text: string) => {
      setPending(text);
      try {
        let id = activeId;
        if (!id) {
          const conv = await api<Conversation>("/conversations", { method: "POST", body: {} });
          id = conv.id;
          setActiveId(id);
        }
        const res = await api<SendResult>(`/conversations/${id}/messages`, { method: "POST", body: { content: text } });
        setMessages((prev) => [...prev, res.user_message, res.assistant_message]);
        if (res.assistant_message.evidence) {
          setEvidence({ messageId: res.assistant_message.id, evidence: res.assistant_message.evidence });
        }
        setConversations((prev) => [res.conversation, ...prev.filter((c) => c.id !== res.conversation.id)]);
      } catch (e) {
        toast.error(e instanceof ApiError ? e.message : "The question could not be answered");
      } finally {
        setPending(null);
      }
    },
    [activeId],
  );

  // Deep link: /ask?q=... (used by the overview's signal links).
  useEffect(() => {
    if (autoAsked.current) return;
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      autoAsked.current = true;
      window.history.replaceState(null, "", "/ask");
      // Defer so the send's state updates happen outside the effect body.
      void Promise.resolve().then(() => send(q));
    }
  }, [send]);

  function newConversation() {
    setActiveId(null);
    setMessages([]);
    setEvidence(null);
  }

  async function rename(id: string, title: string) {
    setRenaming(null);
    const clean = title.trim();
    if (!clean) return;
    try {
      const updated = await api<Conversation>(`/conversations/${id}`, { method: "PATCH", body: { title: clean } });
      setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Rename failed");
    }
  }

  async function remove(id: string) {
    try {
      await api(`/conversations/${id}`, { method: "DELETE" });
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeId) newConversation();
      toast("Conversation deleted");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function feedback(message: Message, helpful: boolean) {
    if (!activeId) return;
    try {
      const updated = await api<Message>(`/conversations/${activeId}/messages/${message.id}/feedback`, {
        method: "POST",
        body: { helpful },
      });
      setMessages((prev) => prev.map((m) => (m.id === message.id ? updated : m)));
      toast(helpful ? "Marked as helpful" : "Thanks. Flagged for review");
    } catch {
      toast.error("Feedback was not saved");
    }
  }

  function showEvidence(m: Message) {
    if (!m.evidence) return;
    setEvidence({ messageId: m.id, evidence: m.evidence });
    if (window.matchMedia("(max-width: 1279px)").matches) setSheetOpen(true);
  }

  const active = conversations.find((c) => c.id === activeId);

  return (
    <div className="flex h-[calc(100dvh-3rem)] md:h-[100dvh]">
      {/* Conversation list */}
      <section aria-label="Conversations" className="hidden w-60 shrink-0 flex-col border-r border-line lg:flex">
        <div className="flex h-14 items-center justify-between px-3">
          <h2 className="text-[13px] font-medium text-ink-soft">Conversations</h2>
          <Button variant="ghost" size="icon" onClick={newConversation} aria-label="New conversation" title="New conversation">
            <Plus size={16} />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 pb-3">
          {loadError && <p className="px-2 text-[12.5px] text-error">{loadError}</p>}
          {!loadError && conversations.length === 0 && (
            <p className="px-2 text-[12.5px] leading-relaxed text-muted">Questions you ask are kept here.</p>
          )}
          {conversations.map((c) => (
            <div key={c.id} className="group relative">
              {renaming === c.id ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void rename(c.id, new FormData(e.currentTarget).get("title") as string);
                  }}
                >
                  <label className="sr-only" htmlFor={`rename-${c.id}`}>
                    Conversation title
                  </label>
                  <input
                    id={`rename-${c.id}`}
                    name="title"
                    defaultValue={c.title}
                    autoFocus
                    onBlur={(e) => void rename(c.id, e.target.value)}
                    onKeyDown={(e) => e.key === "Escape" && setRenaming(null)}
                    className="h-8 w-full rounded-[var(--radius-ctl)] border border-accent bg-surface px-2 text-[13px] outline-none"
                  />
                </form>
              ) : (
                <button
                  type="button"
                  onClick={() => void openConversation(c.id)}
                  aria-current={c.id === activeId ? "true" : undefined}
                  className={cn(
                    "flex w-full flex-col rounded-[var(--radius-ctl)] px-2 py-1.5 pr-8 text-left transition-colors",
                    c.id === activeId ? "bg-surface shadow-[0_0_0_1px_var(--border)]" : "hover:bg-sunken",
                  )}
                >
                  <span className="truncate text-[13px]">{c.title}</span>
                  <span className="text-[11.5px] text-muted">{relativeTime(c.updated_at)}</span>
                </button>
              )}
              {renaming !== c.id && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      aria-label={`Options for ${c.title}`}
                      className="absolute right-1 top-1.5 flex h-7 w-7 items-center justify-center rounded-md text-muted opacity-0 hover:bg-sunken focus:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 data-[state=open]:opacity-100"
                    >
                      <MoreHorizontal size={15} />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" side="right">
                    <DropdownMenuItem onSelect={() => setRenaming(c.id)}>Rename</DropdownMenuItem>
                    <DropdownMenuItem destructive onSelect={() => void remove(c.id)}>
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Thread */}
      <section aria-label="Answers" className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line px-5">
          <h1 className="truncate text-[15px] font-semibold tracking-tight">{active?.title ?? "Ask about your statements"}</h1>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={newConversation} className="lg:hidden">
              <Plus size={15} /> New
            </Button>
            {evidence && (
              <Button variant="ghost" size="sm" onClick={() => setSheetOpen(true)} className="xl:hidden">
                <PanelRightOpen size={15} /> Evidence
              </Button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto" aria-live="polite">
          {loadError && !messages.length ? (
            <div className="mx-auto max-w-[720px] px-5 py-8">
              <ErrorState message={loadError} onRetry={() => void loadConversations()} />
            </div>
          ) : messages.length === 0 && !pending ? (
            <div className="mx-auto flex max-w-[720px] flex-col px-5 pb-10 pt-[12vh]">
              <h2 className="text-[26px] font-semibold leading-tight tracking-tight">What do you want to know?</h2>
              <p className="mt-2 max-w-[56ch] text-[14.5px] leading-relaxed text-ink-soft">
                Totals are computed by the database over verified rows only. Every answer links to the rows it came from.
              </p>
              <div className="mt-8 grid gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => void send(s)}
                    className="rounded-[var(--radius-ctl)] border border-line bg-surface px-3.5 py-3 text-left text-[13.5px] text-ink-soft transition-colors hover:border-line-strong hover:text-ink"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto flex max-w-[760px] flex-col gap-7 px-5 py-8">
              {messages.map((m) => (
                <MessageView
                  key={m.id}
                  message={m}
                  selected={evidence?.messageId === m.id}
                  onShowEvidence={() => showEvidence(m)}
                  onFeedback={(helpful) => void feedback(m, helpful)}
                />
              ))}
              {pending && (
                <>
                  <MessageView
                    message={{ id: "pending", role: "user", content: pending, route_kind: null, created_at: "", kpis: [], source_summary: null, evidence: null, is_helpful: null }}
                  />
                  <div className="space-y-2.5" aria-label="Answering">
                    <div className="skeleton h-4 w-40" />
                    <div className="skeleton h-4 w-full max-w-[520px]" />
                    <div className="skeleton h-4 w-2/3 max-w-[380px]" />
                  </div>
                </>
              )}
              <div ref={threadEnd} />
            </div>
          )}
        </div>

        <Composer onSend={(t) => void send(t)} disabled={Boolean(pending)} />
      </section>

      {/* Evidence: docked on xl, sheet below */}
      <aside aria-label="Evidence" className="hidden w-[380px] shrink-0 border-l border-line bg-surface xl:block">
        <EvidencePanel evidence={evidence?.evidence ?? null} />
      </aside>

      <Dialog.Root open={sheetOpen} onOpenChange={setSheetOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-ink/30 xl:hidden" />
          <Dialog.Content className="rise-in fixed inset-x-0 bottom-0 z-50 flex max-h-[85dvh] flex-col rounded-t-[var(--radius-panel)] border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] sm:inset-y-0 sm:left-auto sm:right-0 sm:max-h-none sm:w-[400px] sm:rounded-none sm:border-l sm:border-t-0 xl:hidden">
            <Dialog.Title className="sr-only">Evidence</Dialog.Title>
            <Dialog.Description className="sr-only">Rows and query plan behind the selected answer</Dialog.Description>
            <Dialog.Close asChild>
              <button type="button" aria-label="Close evidence" className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-[var(--radius-ctl)] text-muted hover:bg-sunken">
                <X size={16} />
              </button>
            </Dialog.Close>
            <div className="min-h-0 flex-1">
              <EvidencePanel evidence={evidence?.evidence ?? null} />
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
