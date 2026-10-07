import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-[var(--radius-panel)] border border-line bg-surface p-4 text-[13.5px]">
      <AlertCircle size={16} className="mt-0.5 shrink-0 text-error" aria-hidden />
      <div className="flex-1">
        <p className="font-medium text-ink">Something went wrong</p>
        <p className="mt-0.5 text-ink-soft">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2.5" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-9" style={{ opacity: 1 - i * 0.15 }} />
      ))}
    </div>
  );
}
