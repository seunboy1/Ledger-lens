"""
Decides whether a question should be answered by SQL aggregation or by
semantic (pgvector) search — the mechanism that keeps the LLM from ever
reading a full corpus of transactions. See docs/architecture.md §5.
"""

import re
from enum import Enum


class RetrievalRoute(str, Enum):
    sql = "sql"
    semantic = "semantic"


_AGGREGATION_PATTERNS = [
    r"\btotal\b",
    r"\bsum\b",
    r"\bhow much\b",
    r"\baverage\b",
    r"\bcount\b",
    r"\bbalance\b",
    r"\bnet\b",
    r"\bbetween\b.*\band\b",  # date ranges
]

_SEMANTIC_HINTS = [
    r"\blook like\b",
    r"\bsimilar\b",
    r"\bsubscription\b",
    r"\bsuspicious\b",
    r"\bunusual\b",
    r"\bkind of\b",
    r"\bcategory\b",
    r"\bbett?ing\b|\bgambl",
    r"\bbounced?\b|\breturned\b",
    r"\bother lenders?\b",
    r"\bwhat kind\b|\bwhich (?:merchants?|payees?)\b",
]


def route_question(question: str) -> RetrievalRoute:
    """
    Rule-based first pass — cheap, fast, and correct for the large majority
    of financial questions, which are aggregations. An LLM-based classifier
    can replace or augment this later for ambiguous phrasing, but the
    contract (return one of two routes, never "read everything") stays
    the same regardless of what implements it.
    """

    q = question.lower()

    if any(re.search(p, q) for p in _SEMANTIC_HINTS):
        return RetrievalRoute.semantic

    if any(re.search(p, q) for p in _AGGREGATION_PATTERNS):
        return RetrievalRoute.sql

    # Default to SQL: most transaction questions are filterable/aggregatable,
    # and SQL is strictly cheaper than an embedding + vector search round trip.
    return RetrievalRoute.sql
