import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { DocStatus } from "@/types/api";
import { cn } from "@/lib/cn";

const MAP: Record<DocStatus, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  reconciled: { label: "Reconciled", className: "bg-credit-soft text-credit", Icon: CheckCircle2 },
  needs_review: { label: "Needs review", className: "bg-warn-soft text-warn", Icon: AlertTriangle },
  processing: { label: "Processing", className: "bg-sunken text-ink-soft", Icon: Loader2 },
  uploaded: { label: "Uploading", className: "bg-sunken text-ink-soft", Icon: Loader2 },
  failed: { label: "Failed", className: "bg-error-soft text-error", Icon: XCircle },
};

export function StatusBadge({ status, className }: { status: DocStatus; className?: string }) {
  const { label, className: tone, Icon } = MAP[status];
  const spinning = status === "processing" || status === "uploaded";
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[12px] font-medium", tone, className)}>
      <Icon size={12} strokeWidth={2} className={cn(spinning && "animate-spin motion-reduce:animate-none")} aria-hidden />
      {label}
    </span>
  );
}
