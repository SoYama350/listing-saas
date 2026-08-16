---
name: create-pdf
description: This skill should be used when the user asks to "create a PDF", "generate a PDF", "convert markdown to PDF", "make a PDF document", "export as PDF", "save as PDF", or mentions producing a PDF from markdown, text, or documentation. Handles styled PDF generation with tables, code blocks, RTL/Arabic text support, page numbers, and custom theming.
---

# Create PDF

Generate a styled PDF document from a Markdown (or text) source. The skill bundles a reusable Python script (`markdown` + `WeasyPrint`) that converts Markdown to a clean, paginated PDF with tables, fenced code blocks, blockquotes, page numbers, and right-to-left (Arabic) text support.

## When to use

Trigger this skill whenever the goal is to produce a `.pdf` file from written content — for example:

- "make a PDF of this README"
- "convert the conversation to PDF"
- "generate a PDF report"
- "export this document as PDF"
- "create a PDF version of these notes"

## Workflow

### 1. Prepare the Markdown source

Write or locate the Markdown (`.md`) file to convert. If the content is not yet in a file, write it to one first (e.g. `report.md`). Plain text also works but Markdown gives tables, headings, and code formatting.

### 2. Install dependencies (if not present)

The script auto-installs `markdown` and `weasyprint` on first run, but to install explicitly:

```bash
uv pip install --quiet markdown weasyprint
```

> WeasyPrint requires system libraries (`pango`, `cairo`). On Debian/Ubuntu: `sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0`. Most containers already have these.

### 3. Run the script

```bash
python .agents/skills/create-pdf/scripts/build_pdf.py <input.md> [-o output.pdf] [--css style.css] [--title "Doc Title"]
```

Arguments:

| Argument | Required | Description |
|---|---|---|
| `input` | Yes | Path to the Markdown (`.md`) file |
| `-o, --output` | No | Output PDF path (default: input name with `.pdf`) |
| `--css` | No | Path to a custom CSS stylesheet (overrides the default theme) |
| `--title` | No | Document title; injected as an H1 and shown in the page footer |

### 4. Verify the PDF

Confirm the output is a valid PDF and check the page count:

```bash
python -c "from pypdf import PdfReader; print('pages:', len(PdfReader('output.pdf').pages))"
```

Or check the header:

```bash
head -c 8 output.pdf   # should print: %PDF-1.7
```

## Default styling

The built-in stylesheet (`DEFAULT_CSS` in `scripts/build_pdf.py`) provides:

- A4 page size, 2 cm margins
- Page numbers in the footer (`Page X / Y`)
- Document title in the footer (pulled from the first H1)
- Blue headings (`#1a3a6b`) with bottom borders
- Dark code blocks (`#0f1115` background) with wrapping
- Styled tables (blue header row, zebra striping)
- Blue-accent blockquotes
- RTL/Arabic support via `dir="rtl"` or `lang="ar"`
- Page-break avoidance for headings, tables, and code blocks

## Customizing the look

For custom colors, fonts, page size, or themes, write a CSS file and pass `--css`:

```bash
python .agents/skills/create-pdf/scripts/build_pdf.py report.md --css dark.css -o report.pdf
```

See **`references/styling.md`** for full CSS guidance: page setup, named pages, RTL, color themes (dark, minimal), code highlighting, page-break control, and font availability.

## Arabic / RTL content

To render an Arabic section right-to-left, wrap it in inline HTML within the Markdown:

```markdown
<div dir="rtl">
هذا النص بالعربية سيظهر من اليمين إلى اليسار.
</div>
```

The default font stack includes `"Noto Sans Arabic"` (install with `apt install fonts-noto` if missing).

## Tips

- **Long tables**: the default CSS wraps cell content and avoids breaking tables across pages. For very wide tables, reduce `table { font-size: 8.5pt; }` in a custom CSS.
- **Force a page break**: insert `<div style="page-break-after: always;"></div>` in the Markdown.
- **Code highlighting**: if `pygments` is installed, fenced code blocks get token classes automatically.
- **Multiple documents**: run the script once per Markdown file; or concatenate Markdown files with `cat` before converting.

## Additional Resources

### Scripts

- **`scripts/build_pdf.py`** — The Markdown → PDF converter. Accepts `input.md`, optional `-o`, `--css`, `--title`. Auto-installs `markdown` and `weasyprint` if missing.

### Reference Files

- **`references/styling.md`** — Detailed CSS reference: `@page` rules, page numbers, named pages, RTL/Arabic, dark/minimal themes, code highlighting, page breaks, fonts.
