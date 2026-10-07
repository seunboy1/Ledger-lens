/** Brand mark: a lens ring over a ledger rule. Simple geometry, token colours. */
export function LensMark({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <rect x="1" y="1" width="22" height="22" rx="6" fill="var(--ink)" />
      <path d="M6 16.5h12" stroke="var(--bg)" strokeOpacity="0.45" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="11" cy="10.5" r="4" stroke="var(--bg)" strokeWidth="1.75" />
      <path d="m14 13.5 3 3" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
