"use client";

import { setStored, useStored } from "@/lib/stored";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/cn";

type Mode = "system" | "light" | "dark";
const KEY = "ledgerlens.theme";

function apply(mode: Mode) {
  const root = document.documentElement;
  if (mode === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", mode);
}

export function ThemeToggle({ className }: { className?: string }) {
  const stored = useStored(KEY);
  const mode: Mode = stored === "light" || stored === "dark" ? stored : "system";

  function choose(next: Mode) {
    apply(next);
    setStored(KEY, next);
  }

  const options: { value: Mode; label: string; Icon: typeof Sun }[] = [
    { value: "system", label: "System theme", Icon: Monitor },
    { value: "light", label: "Light theme", Icon: Sun },
    { value: "dark", label: "Dark theme", Icon: Moon },
  ];

  return (
    <div role="radiogroup" aria-label="Theme" className={cn("inline-flex rounded-[var(--radius-ctl)] border border-line p-0.5", className)}>
      {options.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mode === value}
          aria-label={label}
          title={label}
          onClick={() => choose(value)}
          className={cn(
            "flex h-6 w-7 items-center justify-center rounded-[6px] text-muted transition-colors hover:text-ink",
            mode === value && "bg-sunken text-ink",
          )}
        >
          <Icon size={13} strokeWidth={1.75} />
        </button>
      ))}
    </div>
  );
}
