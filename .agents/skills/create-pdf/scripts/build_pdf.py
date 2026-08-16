#!/usr/bin/env python3
"""Convert a Markdown file to a styled PDF.

General-purpose markdown -> PDF generator using Python `markdown` + WeasyPrint.
Supports tables, fenced code, syntax highlighting via pygments (optional), RTL
text (e.g. Arabic), custom CSS, and a built-in page footer with page numbers.

Usage:
    python build_pdf.py <input.md> [-o output.pdf] [--css style.css] [--title "Doc Title"]

If --css is omitted, a clean default stylesheet is used (see DEFAULT_CSS below).
If -o is omitted, output path = input path with .pdf extension.

Dependencies (installed automatically if missing):
    markdown, weasyprint
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "markdown", "weasyprint"])
    import markdown

try:
    from weasyprint import CSS, HTML
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "weasyprint"])
    from weasyprint import CSS, HTML


DEFAULT_CSS = """
@page {
    size: A4;
    margin: 2cm 1.8cm;
    @bottom-center { content: string(doctitle); font-size: 8pt; color: #888; }
    @bottom-right  { content: "Page " counter(page) " / " counter(pages); font-size: 8pt; color: #888; }
}
* { box-sizing: border-box; }
body {
    font-family: "DejaVu Sans", "Noto Sans", "Noto Sans Arabic", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1a1a1a;
}
/* RTL support: any element with dir="rtl" or lang="ar" flips direction */
[dir="rtl"], [lang="ar"] { direction: rtl; text-align: right; }
h1 {
    string-set: doctitle content();
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
/* pygments syntax highlighting (if codehilite extension used) */
.codehilite .k { color: #ff79c6; }
.codehilite .s { color: #f1fa8c; }
.codehilite .n { color: #e6e8ee; }
.codehilite .c { color: #6272a4; font-style: italic; }
"""


def md_to_pdf(
    md_path: Path,
    out_path: Path,
    css_str: str | None = None,
    title: str | None = None,
) -> None:
    """Convert a markdown file to a styled PDF."""
    md_text = md_path.read_text(encoding="utf-8")

    extensions = ["tables", "fenced_code", "toc", "sane_lists", "nl2br"]
    # add code highlighting if pygments is available
    try:
        import pygments  # noqa: F401

        extensions.append("codehilite")
    except ImportError:
        pass

    html_body = markdown.markdown(md_text, extensions=extensions)

    # inject a title heading if provided and the doc doesn't start with an h1
    if title and not md_text.lstrip().startswith("# "):
        html_body = f"<h1>{title}</h1>\n{html_body}"

    css = css_str or DEFAULT_CSS
    full_html = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{html_body}</body></html>"
    )
    HTML(string=full_html).write_pdf(str(out_path))
    print(f"PDF generated: {out_path} ({out_path.stat().st_size // 1024} KB)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert Markdown to a styled PDF.")
    ap.add_argument("input", help="Path to the input .md file")
    ap.add_argument("-o", "--output", help="Output .pdf path (default: input with .pdf)")
    ap.add_argument("--css", help="Path to a custom CSS file (overrides default style)")
    ap.add_argument("--title", help="Document title (shown as H1 + page footer)")
    args = ap.parse_args()

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        sys.exit(f"Input file not found: {md_path}")

    out_path = (
        Path(args.output).resolve()
        if args.output
        else md_path.with_suffix(".pdf")
    )

    css_str = None
    if args.css:
        css_path = Path(args.css).resolve()
        if not css_path.exists():
            sys.exit(f"CSS file not found: {css_path}")
        css_str = css_path.read_text(encoding="utf-8")

    md_to_pdf(md_path, out_path, css_str=css_str, title=args.title)


if __name__ == "__main__":
    main()
