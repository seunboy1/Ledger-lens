from datetime import date
from decimal import Decimal

import pytest

from app.services.planner import Intent, build_plan
from app.services.router import RetrievalRoute, route_question

BANKS = ["Kestrel Bank", "Oakline Microfinance Bank", "Harbour Trust Bank"]
TODAY = date(2026, 10, 1)


def plan(q):
    return build_plan(q, known_banks=BANKS, today=TODAY)


def test_month_without_year_means_most_recent():
    p = plan("total debits in March")
    assert p.date_range.start == date(2026, 3, 1) and p.date_range.end == date(2026, 4, 1)
    assert p.intent == Intent.total and p.transaction_type == "debit"


def test_bank_matches_on_distinctive_word_only():
    assert plan("credits at Oakline").bank == "Oakline Microfinance Bank"
    assert plan("what did the bank charge me").bank is None


def test_balance_question_has_no_narration_keywords():
    p = plan("balance at the end of September 2026")
    assert p.intent == Intent.balance and p.keywords == []


def test_amount_bounds_and_limit():
    p = plan("top 5 payments over 50k last quarter")
    assert p.intent == Intent.largest and p.limit == 5 and p.min_amount == Decimal(50000)


@pytest.mark.parametrize(
    "q,route",
    [
        ("which of these look like subscriptions", RetrievalRoute.semantic),
        ("any betting spend?", RetrievalRoute.semantic),
        ("how much did I spend in August", RetrievalRoute.sql),
        ("show debits at Kestrel", RetrievalRoute.sql),
    ],
)
def test_routing(q, route):
    assert route_question(q) == route
