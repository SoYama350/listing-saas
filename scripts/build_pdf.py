"""Generate docs/CONVERSATION.pdf from docs/CONVERSATION.md."""
from __future__ import annotations

from pathlib import Path

import markdown
from weasyprint import CSS, HTML

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "CONVERSATION.md"
OUT = ROOT / "docs" / "CONVERSATION.pdf"

CSS_STR = """
@page {
    size: A4;
    margin: 2cm 1.8cm;
    @bottom-center { content: "Listing SaaS - Conversation & Project History"; font-size: 8pt; color: #888; }
    @bottom-right  { content: "Page " counter(page) " / " counter(pages); font-size: 8pt; color: #888; }
}
* { box-sizing: border-box; }
body {
    font-family: "DejaVu Sans", "Noto Sans", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1a1a1a;
}
h1 {
    font-size: 20pt;
    color: #1a3a6b;
    border-bottom: 3px solid #5b9dff;
    padding-bottom: 8px;
    margin-top: 0;
}
h2 {
    font-size: 15pt;
    color: #1a3a6b;
    margin-top: 26px;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 4px;
}
h3 { font-size: 12pt; color: #2a4a7b; margin-top: 20px; }
h4 { font-size: 11pt; color: #444; margin-top: 16px; }
p { margin: 8px 0; }
blockquote {
    border-left: 4px solid #5b9dff;
    background: #f4f8ff;
    margin: 10px 0;
    padding: 8px 14px;
    color: #333;
    font-size: 10pt;
}
blockquote p { margin: 4px 0; }
code {
    font-family: "DejaVu Sans Mono", "Courier New", monospace;
    background: #f0f2f5;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 9pt;
    color: #b03060;
    word-break: break-word;
}
pre {
    background: #0f1115;
    color: #e6e8ee;
    padding: 12px 14px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 8.5pt;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
}
pre code { background: none; color: inherit; padding: 0; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 9.5pt;
}
th, td {
    border: 1px solid #d0d7de;
    padding: 6px 9px;
    text-align: left;
    vertical-align: top;
}
th { background: #1a3a6b; color: #fff; font-weight: 600; }
tr:nth-child(even) { background: #f6f8fa; }
ul, ol { padding-left: 22px; }
li { margin: 3px 0; }
a { color: #5b9dff; text-decoration: none; }
hr { border: none; border-top: 1px solid #d0d7de; margin: 24px 0; }
strong { color: #111; }
em { color: #555; }
h1, h2, h3, h4 { page-break-after: avoid; }
table, pre, blockquote { page-break-inside: avoid; }
"""


def build() -> None:
    md_text = SRC.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "nl2br"],
    )
    full_html = f"<!doctype html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    HTML(string=full_html).write_pdf(str(OUT), stylesheets=[CSS(string=CSS_STR)])
    print(f"PDF generated: {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
