export type RouteKind = "sql" | "semantic";
export type Tone = "credit" | "debit" | "neutral";
export type DocStatus = "uploaded" | "processing" | "reconciled" | "needs_review" | "failed";

export type Session = {
  tenantId: string;
  workspace: string;
  user: { name: string; role: string };
};

export type Conversation = { id: string; title: string; updated_at: string };

export type Kpi = { label: string; value: string; tone: Tone };

export type EvidenceRow = {
  id: string;
  date: string;
  amount: string;
  type: "credit" | "debit";
  raw_label: string;
  bank: string;
  description: string;
  focused: boolean;
};

export type Evidence = {
  summary_title: string;
  summary_subtitle: string;
  lineage: { title: string; detail: string }[];
  rows: EvidenceRow[];
  total_rows: number;
  isolation_note: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  route_kind: RouteKind | null;
  created_at: string;
  kpis: Kpi[];
  source_summary: string | null;
  evidence: Evidence | null;
  is_helpful: boolean | null;
  engine?: "agent" | "deterministic" | null;
};

export type SendResult = {
  conversation: Conversation;
  user_message: Message;
  assistant_message: Message;
};

export type DocumentSummary = {
  id: string;
  filename: string;
  bank_name: string | null;
  status: DocStatus;
  page_count: number | null;
  reconciliation_score: number | null;
  transaction_count: number;
  period_start: string | null;
  period_end: string | null;
  error: string | null;
  created_at: string;
};

export type Txn = {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: "credit" | "debit";
  raw_label: string;
  bank: string;
  balance_after: number | null;
  expected_balance: number | null;
  reconciled: boolean;
  repair_source: string | null;
  page_number: number | null;
};

export type DocumentDetail = DocumentSummary & {
  proof: {
    opening: number | null;
    closing_printed: number | null;
    closing_computed: number | null;
    total_credits: number;
    total_debits: number;
    rows_total: number;
    rows_verified: number;
    document_check_ok: boolean | null;
    pending_ai_repairs: number;
  };
  layout: {
    fingerprint: string;
    amount_convention: string | null;
    date_format: string | null;
    induced_by: string | null;
    times_reused: number;
    columns: Record<string, number>;
  } | null;
  chunks: { done: number; failed: number; total: number };
  failing_rows: Txn[];
};

export type Workspace = {
  tenant: { id: string; name: string };
  banks: { name: string; transactions: number; from: string; to: string }[];
  documents: Record<DocStatus, number>;
  verified_transactions: number;
  layouts_learned: number;
  currency: string;
};

export type MonthRow = {
  month: string;
  inflow: number;
  outflow: number;
  net: number;
  count: number;
  closing_balance: number;
};

export type Signal = { count: number; total: number; transaction_ids: string[] };

export type Overview = {
  months: MonthRow[];
  kpis: {
    avg_monthly_inflow: number;
    avg_monthly_outflow: number;
    net_volatility: number;
    min_balance: number | null;
    avg_balance: number | null;
    closing_balance: number | null;
  };
  salary: {
    detected: boolean;
    narration: string;
    bank: string;
    average_amount: number;
    typical_day: number;
    months: number;
  } | null;
  signals: Record<"betting" | "other_lender_repayments" | "returned_items", Signal>;
  counterparties: { name: string; total: number; count: number; share: number }[];
  documents: Partial<Record<DocStatus, number>>;
};
