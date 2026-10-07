"""
Synthetic bank statements for the demo workspace and the end-to-end tests.

Each statement is rendered to a real PDF in a different bank layout, so the
demo exercises the actual pipeline (table extraction, layout fingerprinting,
spec induction, deterministic parse, reconciliation) instead of inserting
rows directly. All names, banks and figures are fictional.

Layouts:
  * Kestrel Bank      - separate Debit / Credit columns, dd/mm/yyyy
  * Harbour Trust     - one signed Amount column, yyyy-mm-dd
  * Oakline MFB       - Amount plus a DR/CR flag column, dd-Mon-yyyy
  * Palmgrove Bank    - Withdrawals / Lodgements columns, dd.mm.yyyy (the
                        "sample upload" in the UI: a layout the demo has not seen)
  * Crestline Bank    - Money Out / Money In columns, dd Mon yyyy
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


@dataclass
class Line:
    day: date
    narration: str
    amount: Decimal  # positive = credit, negative = debit


@dataclass
class Statement:
    filename: str
    bank: str
    account_name: str
    account_number: str
    layout: str  # "kestrel" | "harbour" | "oakline" | "palmgrove" | "crestline"
    opening: Decimal
    start: date
    end: date
    lines: list[Line] = field(default_factory=list)
    # (line index, wrong printed amount) to simulate a misprinted row.
    misprint: tuple[int, Decimal] | None = None

    @property
    def closing(self) -> Decimal:
        return self.opening + sum((l.amount for l in self.lines), Decimal(0))


def _d(value: float) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _months(start: date, end: date):
    current = date(start.year, start.month, 1)
    while current <= end:
        yield current
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


def _clamp(month: date, day: int) -> date:
    for d in range(day, 0, -1):
        try:
            return month.replace(day=d)
        except ValueError:
            continue
    return month


POS_MERCHANTS = [
    "POS PURCHASE HALLMARK SUPERMART IKEJA",
    "POS PURCHASE GREENLEAF PHARMACY",
    "POS PURCHASE MAINLAND FUEL STATION",
    "POS PURCHASE KITCHEN 24 LEKKI",
    "WEB PURCHASE TRAVELDESK NG",
    "POS PURCHASE CITYMART YABA",
]


def kestrel_salary_account(seed: int = 7) -> Statement:
    rng = random.Random(seed)
    s = Statement(
        filename="kestrel-bank-apr-sep-2026.pdf",
        bank="Kestrel Bank Plc",
        account_name="CHIDINMA OKAFOR",
        account_number="0123994471",
        layout="kestrel",
        opening=_d(412350.18),
        start=date(2026, 4, 1),
        end=date(2026, 9, 30),
    )
    for month in _months(s.start, s.end):
        s.lines.append(Line(_clamp(month, 1), "GYMHOUSE MONTHLY MEMBERSHIP", -_d(15000)))
        s.lines.append(Line(_clamp(month, 3), "STREAMFLIX NG SUBSCRIPTION", -_d(4400)))
        s.lines.append(Line(_clamp(month, 5), "QUICKCRED LOAN REPAYMENT REF QC-88213", -_d(62500)))
        s.lines.append(Line(_clamp(month, 10), "FIBRELINK HOME INTERNET", -_d(18500)))
        s.lines.append(Line(_clamp(month, 12), "POWERGRID PREPAID TOKEN", -_d(rng.choice([15000, 20000, 25000]))))
        for _ in range(rng.randint(6, 9)):
            s.lines.append(Line(_clamp(month, rng.randint(2, 28)), rng.choice(POS_MERCHANTS), -_d(rng.randint(25, 450) * 100)))
        for _ in range(rng.randint(1, 3)):
            s.lines.append(Line(_clamp(month, rng.randint(2, 28)), "LUCKYPLAY BET WALLET FUNDING", -_d(rng.choice([2000, 5000, 10000]))))
        s.lines.append(Line(_clamp(month, rng.randint(2, 20)), "AIRTIME TOPUP 0803****114", -_d(rng.choice([1000, 2000, 5000]))))
        s.lines.append(Line(_clamp(month, 25), "SALARY PAYMENT LAGOON LOGISTICS LTD", _d(845000)))
        s.lines.append(Line(_clamp(month, 25), "STAMP DUTY", -_d(50)))
        s.lines.append(Line(_clamp(month, 27), "TRF TO HARBOUR TRUST SAVINGS", -_d(150000)))
        s.lines.append(Line(_clamp(month, 28), "SMS ALERT CHARGES", -_d(300)))
        if month.month in (5, 8):
            s.lines.append(Line(_clamp(month, rng.randint(14, 20)), "TRF FROM EMEKA OKAFOR", _d(rng.choice([50000, 75000]))))
        if month.month == 7:
            s.lines.append(Line(_clamp(month, 6), "RTN CHQ 000184 INSUFFICIENT FUNDS FEE", -_d(5250)))
    s.lines.sort(key=lambda l: l.day)
    return s


def harbour_savings_account(seed: int = 11) -> Statement:
    rng = random.Random(seed)
    s = Statement(
        filename="harbour-trust-savings-apr-sep-2026.pdf",
        bank="Harbour Trust Bank",
        account_name="CHIDINMA OKAFOR",
        account_number="2207718830",
        layout="harbour",
        opening=_d(1250000),
        start=date(2026, 4, 1),
        end=date(2026, 9, 30),
    )
    for month in _months(s.start, s.end):
        s.lines.append(Line(_clamp(month, 27), "INWARD TRANSFER FROM KESTREL BANK", _d(150000)))
        s.lines.append(Line(_clamp(month, 30), "MONTHLY INTEREST CREDIT", _d(rng.randint(780000, 940000) / 100)))
        s.lines.append(Line(_clamp(month, 30), "WITHHOLDING TAX ON INTEREST", -_d(rng.randint(78000, 94000) / 100)))
        if month.month in (6, 9):
            s.lines.append(Line(_clamp(month, rng.randint(8, 18)), "ATM WITHDRAWAL HARBOUR VI BRANCH", -_d(rng.choice([40000, 60000]))))
        if month.month == 8:
            s.lines.append(Line(_clamp(month, 11), "TRF TO OAKLINE MFB BUSINESS ACCT", -_d(200000)))
    s.lines.sort(key=lambda l: l.day)
    return s


def oakline_business_account(seed: int = 19) -> Statement:
    rng = random.Random(seed)
    s = Statement(
        filename="oakline-mfb-business-jul-sep-2026.pdf",
        bank="Oakline Microfinance Bank",
        account_name="CHIDINMA OKAFOR (CO FABRICS)",
        account_number="5100342296",
        layout="oakline",
        opening=_d(96420.50),
        start=date(2026, 7, 1),
        end=date(2026, 9, 30),
    )
    for month in _months(s.start, s.end):
        for _ in range(rng.randint(9, 13)):
            s.lines.append(Line(_clamp(month, rng.randint(1, 28)), "POS SETTLEMENT CO FABRICS", _d(rng.randint(150, 820) * 100)))
        for _ in range(rng.randint(2, 3)):
            s.lines.append(Line(_clamp(month, rng.randint(3, 26)), "TRF TO ADEBAYO TEXTILE SUPPLIES", -_d(rng.randint(900, 2400) * 100)))
        s.lines.append(Line(_clamp(month, 28), "ACCOUNT MAINTENANCE FEE", -_d(1075)))
        if month.month == 8:
            s.lines.append(Line(_clamp(month, 11), "TRF FROM HARBOUR TRUST SAVINGS", _d(200000)))
    s.lines.sort(key=lambda l: l.day)
    return s


def kestrel_joint_account_with_misprint(seed: int = 23) -> Statement:
    """Same layout as the salary account (so its spec is reused), with one misprinted amount."""

    rng = random.Random(seed)
    s = Statement(
        filename="kestrel-bank-joint-jul-sep-2026.pdf",
        bank="Kestrel Bank Plc",
        account_name="CHIDINMA & EMEKA OKAFOR",
        account_number="0123870052",
        layout="kestrel",
        opening=_d(188200),
        start=date(2026, 7, 1),
        end=date(2026, 9, 30),
    )
    for month in _months(s.start, s.end):
        s.lines.append(Line(_clamp(month, 2), "TRF FROM CHIDINMA OKAFOR HOUSEHOLD", _d(120000)))
        s.lines.append(Line(_clamp(month, 2), "TRF FROM EMEKA OKAFOR HOUSEHOLD", _d(120000)))
        s.lines.append(Line(_clamp(month, 4), "SCHOOLHOUSE ACADEMY FEES INSTALMENT", -_d(95000)))
        for _ in range(rng.randint(4, 6)):
            s.lines.append(Line(_clamp(month, rng.randint(5, 27)), rng.choice(POS_MERCHANTS), -_d(rng.randint(30, 520) * 100)))
        s.lines.append(Line(_clamp(month, 28), "SMS ALERT CHARGES", -_d(300)))
    s.lines.sort(key=lambda l: l.day)
    target = next(i for i, l in enumerate(s.lines) if l.day.month == 8 and "POS" in l.narration)
    true_amount = s.lines[target].amount
    s.misprint = (target, true_amount + _d(500))  # e.g. 45,800.00 printed as 45,300.00
    return s


def palmgrove_current_account(seed: int = 31) -> Statement:
    """A fourth layout, used as the in-app sample upload."""

    rng = random.Random(seed)
    s = Statement(
        filename="palmgrove-bank-current-jul-sep-2026.pdf",
        bank="Palmgrove Bank Limited",
        account_name="CHIDINMA OKAFOR",
        account_number="3091145570",
        layout="palmgrove",
        opening=_d(254210.75),
        start=date(2026, 7, 1),
        end=date(2026, 9, 30),
    )
    for month in _months(s.start, s.end):
        s.lines.append(Line(_clamp(month, 1), "RENT CONTRIBUTION FROM EMEKA OKAFOR", _d(150000)))
        s.lines.append(Line(_clamp(month, 3), "LANDLORD RENT TRANSFER ADEOLA PROPERTIES", -_d(180000)))
        for _ in range(rng.randint(3, 5)):
            s.lines.append(Line(_clamp(month, rng.randint(4, 27)), rng.choice(POS_MERCHANTS), -_d(rng.randint(20, 300) * 100)))
        s.lines.append(Line(_clamp(month, 20), "TRF FROM KESTREL BANK SAVINGS", _d(90000)))
        s.lines.append(Line(_clamp(month, 28), "CARD MAINTENANCE FEE", -_d(50)))
    s.lines.sort(key=lambda l: l.day)
    return s


def crestline_household_account(seed: int = 41) -> Statement:
    """A fifth layout: Money Out / Money In columns, 12 months."""

    rng = random.Random(seed)
    s = Statement(
        filename="crestline-bank-household-oct25-sep26.pdf",
        bank="Crestline Bank Plc",
        account_name="EMEKA OKAFOR",
        account_number="4410028815",
        layout="crestline",
        opening=_d(318640.40),
        start=date(2025, 10, 1),
        end=date(2026, 9, 30),
    )
    for month in _months(s.start, s.end):
        s.lines.append(Line(_clamp(month, 26), "SALARY CREDIT HARBOURVIEW HOSPITAL", _d(612000)))
        s.lines.append(Line(_clamp(month, 1), "TRF TO PALMGROVE RENT CONTRIBUTION", -_d(150000)))
        s.lines.append(Line(_clamp(month, 2), "TRF TO KESTREL JOINT HOUSEHOLD", -_d(120000)))
        s.lines.append(Line(_clamp(month, 7), "POWERGRID PREPAID TOKEN", -_d(rng.choice([10000, 15000, 20000]))))
        s.lines.append(Line(_clamp(month, 15), "STREAMFLIX NG SUBSCRIPTION", -_d(4400)))
        for _ in range(rng.randint(4, 7)):
            s.lines.append(Line(_clamp(month, rng.randint(3, 25)), rng.choice(POS_MERCHANTS), -_d(rng.randint(20, 380) * 100)))
        if month.month in (12, 4):
            s.lines.append(Line(_clamp(month, 20), "TRF TO FAMILY UPKEEP ENUGU", -_d(80000)))
    s.lines.sort(key=lambda l: l.day)
    return s


def large_business_account(seed: int = 53, months: int = 24) -> Statement:
    """Two years of daily POS settlements: ~100 pages, so ingestion fans out into several chunks."""

    rng = random.Random(seed)
    start = date(2024, 10, 1)
    end_month = start
    for _ in range(months - 1):
        end_month = date(end_month.year + (end_month.month == 12), end_month.month % 12 + 1, 1)
    end = date(end_month.year + (end_month.month == 12), end_month.month % 12 + 1, 1) - timedelta(days=1)
    s = Statement(
        filename="oakline-mfb-business-oct24-sep26-large.pdf",
        bank="Oakline Microfinance Bank",
        account_name="CHIDINMA OKAFOR (CO FABRICS)",
        account_number="5100342296",
        layout="oakline",
        opening=_d(1250000),
        start=start,
        end=end,
    )
    day = start
    while day <= end:
        for _ in range(rng.randint(3, 7)):
            s.lines.append(Line(day, "POS SETTLEMENT CO FABRICS", _d(rng.randint(40, 600) * 100)))
        if day.weekday() == 1:
            s.lines.append(Line(day, "TRF TO ADEBAYO TEXTILE SUPPLIES", -_d(rng.randint(900, 2600) * 100)))
        if day.day == 28:
            s.lines.append(Line(day, "ACCOUNT MAINTENANCE FEE", -_d(1075)))
            s.lines.append(Line(day, "SALARIES CO FABRICS STAFF", -_d(rng.choice([180000, 210000]))))
        day += timedelta(days=1)
    return s


def demo_statements() -> list[Statement]:
    return [
        kestrel_salary_account(),
        harbour_savings_account(),
        oakline_business_account(),
        kestrel_joint_account_with_misprint(),
    ]


# --- rendering ---------------------------------------------------------------


def _money(value: Decimal) -> str:
    return f"{value:,.2f}"


def _date(value: date, layout: str) -> str:
    if layout == "harbour":
        return value.strftime("%Y-%m-%d")
    if layout == "oakline":
        return value.strftime("%d-%b-%Y")
    if layout == "palmgrove":
        return value.strftime("%d.%m.%Y")
    if layout == "crestline":
        return value.strftime("%d %b %Y")
    return value.strftime("%d/%m/%Y")


def render_pdf(statement: Statement) -> bytes:
    from fpdf import FPDF  # local-profile / test dependency

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, statement.bank, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Statement of account   {statement.start:%d %b %Y} to {statement.end:%d %b %Y}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Account name: {statement.account_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Account number: {statement.account_number}   Currency: NGN", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    layout = statement.layout
    if layout == "kestrel":
        headings = ("Trans Date", "Value Date", "Narration", "Debit", "Credit", "Balance")
        widths = (22, 22, 70, 24, 24, 28)
    elif layout == "harbour":
        headings = ("Date", "Description", "Amount", "Balance")
        widths = (26, 100, 32, 32)
    elif layout == "palmgrove":
        headings = ("Posting Date", "Transaction Details", "Withdrawals", "Lodgements", "Balance")
        widths = (26, 82, 28, 28, 30)
    elif layout == "crestline":
        headings = ("Date", "Narration", "Money Out", "Money In", "Balance")
        widths = (26, 82, 28, 28, 30)
    else:
        headings = ("Txn Date", "Details", "Amount", "DR/CR", "Balance")
        widths = (26, 86, 30, 18, 30)

    pdf.set_font("Helvetica", "", 7.5)
    balance = statement.opening
    with pdf.table(col_widths=widths, text_align="LEFT", line_height=5, repeat_headings=1) as table:
        table.row(headings)

        def blank(n: int) -> list[str]:
            return [""] * n

        opening_row = {
            "kestrel": [_date(statement.start, layout), "", "Opening Balance", "", "", _money(statement.opening)],
            "harbour": [_date(statement.start, layout), "Opening Balance", "", _money(statement.opening)],
            "oakline": [_date(statement.start, layout), "Opening Balance", "", "", _money(statement.opening)],
            "palmgrove": [_date(statement.start, layout), "Balance B/F", "", "", _money(statement.opening)],
            "crestline": [_date(statement.start, layout), "Opening Balance", "", "", _money(statement.opening)],
        }[layout]
        table.row(opening_row)

        for i, line in enumerate(statement.lines):
            balance += line.amount
            printed = line.amount
            if statement.misprint and statement.misprint[0] == i:
                printed = statement.misprint[1]
            magnitude = _money(abs(printed))
            day = _date(line.day, layout)
            if layout == "kestrel":
                value_day = _date(line.day + timedelta(days=0), layout)
                debit, credit = (magnitude, "") if printed < 0 else ("", magnitude)
                table.row([day, value_day, line.narration, debit, credit, _money(balance)])
            elif layout == "harbour":
                table.row([day, line.narration, _money(printed), _money(balance)])
            elif layout in ("palmgrove", "crestline"):
                out, inn = (magnitude, "") if printed < 0 else ("", magnitude)
                table.row([day, line.narration, out, inn, _money(balance)])
            else:
                table.row([day, line.narration, magnitude, "DR" if printed < 0 else "CR", _money(balance)])

        closing_row = {
            "kestrel": [_date(statement.end, layout), "", "Closing Balance", *blank(2), _money(balance)],
            "harbour": [_date(statement.end, layout), "Closing Balance", "", _money(balance)],
            "oakline": [_date(statement.end, layout), "Closing Balance", "", "", _money(balance)],
            "palmgrove": [_date(statement.end, layout), "Balance C/F", "", "", _money(balance)],
            "crestline": [_date(statement.end, layout), "Closing Balance", "", "", _money(balance)],
        }[layout]
        table.row(closing_row)

    return bytes(pdf.output())
