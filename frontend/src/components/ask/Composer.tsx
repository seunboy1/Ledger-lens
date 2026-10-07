"use client";

import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUp } from "lucide-react";

export function Composer({ onSend, disabled }: { onSend: (text: string) => void; disabled?: boolean }) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
    if (ref.current) ref.current.style.height = "auto";
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="shrink-0 border-t border-line bg-bg px-5 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3">
      <div className="mx-auto flex max-w-[760px] items-end gap-2 rounded-[var(--radius-panel)] border border-line-strong bg-surface p-2 pl-3.5 transition-shadow focus-within:border-accent focus-within:[box-shadow:var(--focus-ring)]">
        <label htmlFor="question" className="sr-only">
          Ask a question about your statements
        </label>
        <textarea
          id="question"
          ref={ref}
          rows={1}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={onKeyDown}
          placeholder="Ask about totals, balances, merchants or patterns"
          className="max-h-40 flex-1 resize-none bg-transparent py-1.5 focus-visible:outline-none text-[16px] leading-6 outline-none placeholder:text-muted sm:text-[14.5px]"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send question"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-ctl)] bg-ink text-bg transition-[transform,opacity] active:scale-95 disabled:opacity-30"
        >
          <ArrowUp size={16} />
        </button>
      </div>
      <p className="mx-auto mt-2 max-w-[760px] text-[12px] text-muted">Enter to send, Shift + Enter for a new line.</p>
    </form>
  );
}
