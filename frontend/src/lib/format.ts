const NGN = new Intl.NumberFormat("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const COMPACT = new Intl.NumberFormat("en-NG", { notation: "compact", maximumFractionDigits: 2 });

export function naira(value: number | null | undefined, opts: { signed?: boolean } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const text = `₦${NGN.format(Math.abs(value))}`;
  if (opts.signed) return `${value >= 0 ? "+" : "−"}${text}`;
  return value < 0 ? `−${text}` : text;
}

export function nairaCompact(value: number) {
  return `₦${COMPACT.format(value)}`;
}

export function shortDate(iso: string | null | undefined) {
  if (!iso) return "n/a";
  // Statement dates are calendar dates stored at midnight UTC.
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
}

export function monthLabel(key: string) {
  const [y, m] = key.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
}

export function relativeTime(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return shortDate(iso);
}

export function percent(v: number | null | undefined, digits = 0) {
  if (v === null || v === undefined) return "n/a";
  return `${(v * 100).toFixed(digits)}%`;
}

/** "01 Apr to 28 Sept 2026", or with both years when they differ. */
export function dateRange(from: string | null | undefined, to: string | null | undefined) {
  if (!from || !to) return "n/a";
  const a = new Date(from);
  const b = new Date(to);
  const sameYear = a.getUTCFullYear() === b.getUTCFullYear();
  const start = a.toLocaleDateString("en-GB", { day: "2-digit", month: "short", timeZone: "UTC", ...(sameYear ? {} : { year: "numeric" }) });
  return `${start} to ${shortDate(to)}`;
}
