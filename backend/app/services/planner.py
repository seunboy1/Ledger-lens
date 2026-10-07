"""
Question → structured query plan.

This is the constrained query builder the architecture calls for on the SQL
path (docs/architecture.md §5): a plain-language question is turned into a
small, inspectable set of filters and one aggregation intent. Everything
the plan says is then executed as SQL — the model never sees the corpus and
never performs arithmetic. Because the plan is a plain dataclass, the UI can
render it verbatim as the "Query plan" lineage, and tests can assert on it.

Deterministic on purpose. An LLM-based parser can *propose* a plan later,
but it must still produce this same structure so the execution path never
changes.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum


class Intent(str, Enum):
    total = "total"  # SUM(amount)
    count = "count"  # COUNT(*)
    average = "average"  # AVG(amount)
    largest = "largest"  # ORDER BY amount DESC LIMIT n
    smallest = "smallest"  # ORDER BY amount ASC LIMIT n
    balance = "balance"  # balance statistics
    list = "list"  # plain filtered listing


@dataclass
class DateRange:
    start: date  # inclusive
    end: date  # exclusive
    label: str

    def contains(self, d: date) -> bool:
        return self.start <= d < self.end


@dataclass
class QueryPlan:
    question: str
    intent: Intent = Intent.list
    transaction_type: str | None = None  # "credit" | "debit"
    date_range: DateRange | None = None
    bank: str | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    keywords: list[str] = field(default_factory=list)
    limit: int = 10

    def describe_filters(self) -> str:
        parts: list[str] = []
        if self.transaction_type:
            parts.append(f"type={self.transaction_type}")
        if self.date_range:
            parts.append(f"date={self.date_range.label}")
        if self.bank:
            parts.append(f"bank={self.bank}")
        if self.min_amount is not None:
            parts.append(f"amount>={self.min_amount}")
        if self.max_amount is not None:
            parts.append(f"amount<={self.max_amount}")
        if self.keywords:
            parts.append("narration~" + "/".join(self.keywords))
        return ", ".join(parts) if parts else "none (all rows)"


_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
_MONTHS["sept"] = 9

_CREDIT_WORDS = r"credits?|deposits?|inflows?|income|money in|received|receipts?|salary|salaries|paid in"
_DEBIT_WORDS = r"debits?|withdrawals?|outflows?|spend(?:ing)?|spent|payments?|purchases?|money out|expenses?|charges?|paid out"

_STOPWORDS = {
    "what", "were", "was", "my", "the", "in", "on", "of", "to", "for", "a", "an", "and", "or", "all", "across",
    "accounts", "account", "transactions", "transaction", "total", "totals", "sum", "how", "much", "many", "did",
    "i", "we", "our", "show", "me", "list", "give", "get", "find", "which", "that", "those", "these", "this",
    "from", "with", "by", "at", "is", "are", "be", "have", "has", "had", "do", "does", "please", "over", "under",
    "than", "more", "less", "about", "between", "during", "last", "this", "month", "months", "year", "years",
    "quarter", "q1", "q2", "q3", "q4", "average", "avg", "mean", "count", "number", "largest", "biggest",
    "smallest", "top", "bottom", "highest", "lowest", "balance", "balances", "bank", "credit", "credits",
    "debit", "debits", "deposit", "deposits", "withdrawal", "withdrawals", "spend", "spending", "spent",
    "payment", "payments", "purchase", "purchases", "inflow", "inflows", "outflow", "outflows", "net", "like",
    "look", "looks", "recurring", "subscription", "subscriptions", "any", "there", "it", "its", "them", "they",
    "amount", "amounts", "biggest", "each", "per", "into", "out", "up", "down", "so", "far", "recent", "recently",
    "made", "make", "big", "large", "small", "highest", "lowest", "most", "least", "some", "very", "just", "only",
    "also", "but", "not", "no", "yes", "as", "if", "then", "when", "where", "who", "why", "their", "your", "you",
    "us", "one", "ones", "first", "second", "third", "vs", "versus", "compared", "compare", "show", "tell",
    "end", "start", "beginning", "closing", "opening", "period", "close", "week", "weeks", "day", "days",
    "cashflow", "cash", "flow", "linked", "statement", "statements", "row", "rows", "money", "income",
    "expenses", "expense", "received", "paid", "charges", "charge", "receipts", "receipt",
}


_GENERIC_BANK_WORDS = {"bank", "trust", "microfinance", "mfb", "plc", "limited", "savings", "first", "national", "international"}


def _month_range(year: int, month: int) -> DateRange:
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    return DateRange(start=start, end=end, label=f"{start:%Y-%m}")


def _quarter_range(year: int, q: int) -> DateRange:
    start = date(year, 3 * (q - 1) + 1, 1)
    end_month = 3 * q
    end = date(year + (end_month == 12), (end_month % 12) + 1, 1)
    return DateRange(start=start, end=end, label=f"Q{q} {year}")


def parse_date_range(q: str, today: date | None = None) -> DateRange | None:
    today = today or date.today()

    m = re.search(r"\bbetween\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[a-z]+\s*\d{0,4})\s+and\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[a-z]+\s*\d{0,4})", q)
    if m:
        a = _parse_point(m.group(1), today)
        b = _parse_point(m.group(2), today, end=True)
        if a and b and a < b:
            return DateRange(start=a, end=b, label=f"{a:%Y-%m-%d}..{(b - timedelta(days=1)):%Y-%m-%d}")

    m = re.search(r"\bq([1-4])\b(?:\s*(?:of\s*)?(\d{4}))?", q)
    if m:
        year = int(m.group(2)) if m.group(2) else today.year
        return _quarter_range(year, int(m.group(1)))

    if re.search(r"\blast\s+month\b", q):
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return _month_range(last_prev.year, last_prev.month)
    if re.search(r"\bthis\s+month\b", q):
        return _month_range(today.year, today.month)
    if re.search(r"\blast\s+(\d+)\s+months?\b", q):
        n = int(re.search(r"\blast\s+(\d+)\s+months?\b", q).group(1))
        end = today.replace(day=1)
        end = date(end.year + (end.month == 12), (end.month % 12) + 1, 1)
        y, mth = end.year, end.month
        for _ in range(n):
            mth -= 1
            if mth == 0:
                mth = 12
                y -= 1
        return DateRange(start=date(y, mth, 1), end=end, label=f"last {n} months")
    if re.search(r"\bthis\s+year\b|\byear\s+to\s+date\b|\bytd\b", q):
        return DateRange(start=date(today.year, 1, 1), end=date(today.year + 1, 1, 1), label=str(today.year))
    if re.search(r"\blast\s+year\b", q):
        return DateRange(start=date(today.year - 1, 1, 1), end=date(today.year, 1, 1), label=str(today.year - 1))

    m = re.search(r"\b(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\b(?:\s+(\d{4}))?", q)
    if m:
        month = _MONTHS[m.group(1)]
        year = int(m.group(2)) if m.group(2) else _most_recent_year_for_month(month, today)
        return _month_range(year, month)

    m = re.search(r"\b(20\d{2})\b", q)
    if m:
        y = int(m.group(1))
        return DateRange(start=date(y, 1, 1), end=date(y + 1, 1, 1), label=str(y))

    return None


def _most_recent_year_for_month(month: int, today: date) -> int:
    # "March" with no year means the most recent March that has started.
    return today.year if month <= today.month else today.year - 1


def _parse_point(token: str, today: date, end: bool = False) -> date | None:
    token = token.strip()
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", token)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            point = date(y, mth, d)
        except ValueError:
            return None
        return point + timedelta(days=1) if end else point
    m = re.match(r"([a-z]+)\s*(\d{4})?", token)
    if m and m.group(1) in _MONTHS:
        month = _MONTHS[m.group(1)]
        year = int(m.group(2)) if m.group(2) else _most_recent_year_for_month(month, today)
        rng = _month_range(year, month)
        return rng.end if end else rng.start
    return None


def _parse_amount(text: str) -> Decimal | None:
    cleaned = text.replace(",", "").replace("$", "").replace("₦", "").strip().lower()
    mult = Decimal(1)
    if cleaned.endswith("k"):
        mult = Decimal(1000)
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        mult = Decimal(1_000_000)
        cleaned = cleaned[:-1]
    try:
        return Decimal(cleaned) * mult
    except Exception:  # noqa: BLE001
        return None


def build_plan(question: str, known_banks: list[str] | None = None, today: date | None = None) -> QueryPlan:
    q = question.lower().strip()
    plan = QueryPlan(question=question)

    # --- intent ---------------------------------------------------------
    if re.search(r"\b(average|avg|mean)\b", q):
        plan.intent = Intent.average
    if re.search(r"\b(balance|balances)\b", q) and not re.search(r"\btotal\s+(debit|credit)", q):
        plan.intent = Intent.balance
    if re.search(r"\b(how many|count|number of)\b", q):
        plan.intent = Intent.count
    if re.search(r"\b(largest|biggest|highest|top\s+\d+|top)\b", q):
        plan.intent = Intent.largest
    if re.search(r"\b(smallest|lowest|bottom\s+\d+)\b", q):
        plan.intent = Intent.smallest
    if plan.intent is Intent.list and re.search(r"\b(total|totals|sum|how much|net|inflow|outflow|spend|spent|spending)\b", q):
        plan.intent = Intent.total

    m = re.search(r"\b(?:top|largest|biggest|smallest|lowest|last|first)\s+(\d{1,3})\b(?!\s*(?:months?|days?|weeks?|years?))", q)
    if m:
        plan.limit = max(1, min(int(m.group(1)), 100))
    elif plan.intent in (Intent.largest, Intent.smallest):
        plan.limit = 5

    # --- transaction type ------------------------------------------------
    has_credit = re.search(rf"\b(?:{_CREDIT_WORDS})\b", q) is not None
    has_debit = re.search(rf"\b(?:{_DEBIT_WORDS})\b", q) is not None
    if has_credit and not has_debit:
        plan.transaction_type = "credit"
    elif has_debit and not has_credit:
        plan.transaction_type = "debit"
    if re.search(r"\bnet\b", q):
        plan.transaction_type = None  # net needs both sides

    # --- date -------------------------------------------------------------
    plan.date_range = parse_date_range(q, today)

    # --- bank -------------------------------------------------------------
    for bank in sorted(known_banks or [], key=len, reverse=True):
        b = bank.lower()
        # Match on the distinctive part of the name ("oakline" for
        # "Oakline Microfinance Bank"), never on generic words like "bank".
        distinctive = [t for t in re.findall(r"[a-z]+", b) if t not in _GENERIC_BANK_WORDS and len(t) > 3]
        if b in q or any(re.search(rf"\b{re.escape(t)}\b", q) for t in distinctive):
            plan.bank = bank
            break

    # --- amount bounds -----------------------------------------------------
    m = re.search(r"\b(?:over|above|more than|greater than|at least|>=?)\s*\$?([\d,]+(?:\.\d+)?[km]?)", q)
    if m:
        plan.min_amount = _parse_amount(m.group(1))
    m = re.search(r"\b(?:under|below|less than|at most|<=?)\s*\$?([\d,]+(?:\.\d+)?[km]?)", q)
    if m:
        plan.max_amount = _parse_amount(m.group(1))

    # --- keywords (narration contains) -----------------------------------
    scrub = q
    if plan.bank:
        scrub = scrub.replace(plan.bank.lower(), " ")
    scrub = re.sub(r"[^a-z0-9\s]", " ", scrub)
    tokens = [t for t in scrub.split() if len(t) > 2 and t not in _STOPWORDS and t not in _MONTHS and not t.isdigit()]
    if plan.bank:
        tokens = [t for t in tokens if t not in re.findall(r"[a-z]+", plan.bank.lower())]
    plan.keywords = tokens[:4]

    return plan


def month_label(d: date | datetime) -> str:
    return f"{d:%b %Y}"
