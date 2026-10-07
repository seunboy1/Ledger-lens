"""
Text + layout extraction from a PDF page range.

Digital PDFs go through pdfplumber (word-level positions, used to recover
column boundaries). Scanned pages fall back to PaddleOCR (invoked lazily —
only imported if a page turns out to have no extractable text layer, since
it's a heavy dependency most pages never need).
"""

from dataclasses import dataclass, field
from io import BytesIO

import pdfplumber


@dataclass
class ExtractedRow:
    """One raw table row as read off the page — no interpretation yet."""

    cells: list[str]


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed
    header_tokens: list[str]
    rows: list[ExtractedRow] = field(default_factory=list)
    is_scanned: bool = False


def extract_page_range(pdf_bytes: bytes, page_start: int, page_end: int) -> list[ExtractedPage]:
    """
    page_start/page_end are 1-indexed, inclusive — matching PageRange from
    chunking.py. pdfplumber is 0-indexed internally, so the conversion
    happens at this boundary only.
    """

    pages: list[ExtractedPage] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page_number in range(page_start, page_end + 1):
            if page_number - 1 >= len(pdf.pages):
                break
            page = pdf.pages[page_number - 1]
            table = page.extract_table()

            if table and len(table) > 0:
                header_tokens = [str(c or "").strip() for c in table[0]]
                rows = [ExtractedRow(cells=[str(c or "").strip() for c in r]) for r in table[1:]]
                pages.append(ExtractedPage(page_number=page_number, header_tokens=header_tokens, rows=rows))
            else:
                text = page.extract_text() or ""
                if text.strip():
                    # Has text but no detected table — treat as a page pdfplumber
                    # couldn't structure; still not scanned, just unparsed here.
                    pages.append(ExtractedPage(page_number=page_number, header_tokens=[], rows=[]))
                else:
                    pages.append(
                        ExtractedPage(page_number=page_number, header_tokens=[], rows=[], is_scanned=True)
                    )

    return pages


def count_pages(pdf_bytes: bytes) -> int:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return len(pdf.pages)


def read_statement_header(pdf_bytes: bytes, max_lines: int = 6) -> list[str]:
    """
    The first few text lines of page 1, above the transaction table. This is
    where every statement prints the issuing bank's name, so it is used to
    label the document without asking a model.
    """

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        if not pdf.pages:
            return []
        text = pdf.pages[0].extract_text() or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:max_lines]


def extract_scanned_page(pdf_bytes: bytes, page_number: int) -> ExtractedPage:
    """
    OCR fallback for scanned statements. Imported lazily — most pages never
    reach this path, so PaddleOCR's model download/init cost is only paid
    when it's actually needed.
    """

    from paddleocr import PaddleOCR  # noqa: PLC0415

    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    # A full implementation would rasterize the page to an image (e.g. via
    # PyMuPDF) before calling ocr.ocr(); left as an integration point since
    # it depends on the rasterization backend chosen in production.
    raise NotImplementedError(
        "Scanned-page OCR requires page rasterization (e.g. via PyMuPDF) — "
        "wire this up before enabling scanned-statement support."
    )
