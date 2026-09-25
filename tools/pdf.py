"""PDF-версии КП из печатных страниц docs/print/*.html → docs/pdf/<slug>.pdf и <slug>-no-price.pdf.

Использование: python3 tools/pdf.py            # все авто
               python3 tools/pdf.py <slug> ...  # только указанные
Сначала запустите tools/build.py. Используется установленный Google Chrome (Playwright, channel="chrome").
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
PRINT_DIR = DOCS_DIR / "print"
PDF_DIR = DOCS_DIR / "pdf"
MARGINS = {"top": "14mm", "right": "14mm", "bottom": "16mm", "left": "14mm"}
FOOTER_STYLE = ("width:100%;margin:0 14mm;font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;"
                "font-size:7.5pt;color:#6e6e73;display:flex;justify-content:space-between;")


def footer_template(site: dict) -> str:
    contacts = site["contacts"]
    company = f"«{contacts['company']}»" if contacts.get("company") else None
    left = " · ".join(filter(None, [site["name"], contacts.get("manager"), company,
                                     contacts.get("phone"), contacts.get("email")]))
    return (f'<div style="{FOOTER_STYLE}"><span>{html.escape(left)}</span>'
            '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


def targets(slugs: list[str]) -> list[Path]:
    pages = sorted(PRINT_DIR.glob("*.html"))
    if not slugs:
        return pages
    return [p for p in pages if p.stem in slugs or p.stem.removesuffix("-no-price") in slugs]


def render(pages: list[Path], site: dict) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page()
        for source in pages:
            page.goto(source.resolve().as_uri(), wait_until="networkidle")
            out = PDF_DIR / f"{source.stem}.pdf"
            page.pdf(path=str(out), format="A4", print_background=True, prefer_css_page_size=True,
                     margin=MARGINS, display_header_footer=True,
                     header_template="<span></span>", footer_template=footer_template(site))
            print(f"  {out.relative_to(ROOT)} ({out.stat().st_size // 1024} КБ)")
        browser.close()


def main(argv: list[str]) -> int:
    pages = targets(argv[1:])
    if not pages:
        print("Нет печатных страниц — сначала запустите python3 tools/build.py")
        return 1
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    render(pages, site)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
