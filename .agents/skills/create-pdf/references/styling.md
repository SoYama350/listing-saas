# PDF Styling Reference

Detailed CSS guidance for customizing PDF output from the `create-pdf` skill.

## How styling works

The `build_pdf.py` script renders Markdown → HTML → PDF via WeasyPrint. Styling
is pure CSS, interpreted by WeasyPrint (which supports most CSS 3 Paged Media
specification). Three styling tiers, in priority order:

1. **Custom CSS file** passed via `--css path/to/style.css` (overrides everything)
2. **Built-in `DEFAULT_CSS`** in `scripts/build_pdf.py` (clean blue theme)
3. WeasyPrint's user-agent default (plain)

## Page setup (the `@page` rule)

Control paper size, margins, and page footer/header via `@page`:

```css
@page {
    size: A4;                 /* A4 | Letter | Legal | landscape | custom (e.g. 15cm 20cm) */
    margin: 2cm 1.8cm;        /* top right bottom left, or TRBL shorthand */

    /* Running header (optional) */
    @top-center { content: "Confidential"; font-size: 8pt; color: #999; }

    /* Running footer with page numbers */
    @bottom-right  { content: "Page " counter(page) " / " counter(pages); font-size: 8pt; color: #888; }
    @bottom-center { content: string(doctitle); font-size: 8pt; color: #888; }
}
```

### Pulling the document title into the footer

Set `string-set` on the `h1`, then reference it in `@page`:

```css
h1 { string-set: doctitle content(); }
@page { @bottom-center { content: string(doctitle); } }
```

### Named pages (different layouts per section)

```css
.cover { page: cover; }
@page cover { margin: 0; }
@page cover:first { background: #1a3a6b; }
```

Apply `<div class="cover">…</div>` (via raw HTML in the markdown) to use it.

## RTL / Arabic text

The default CSS already supports right-to-left text. To mark a section as RTL,
either:

- Add `dir="rtl"` via inline HTML in the markdown:
  ```markdown
  <div dir="rtl">
  هذا النص بالعربية.
  </div>
  ```
- Or set the whole document direction in custom CSS:
  ```css
  body { direction: rtl; text-align: right; }
  ```

The default font stack includes `"Noto Sans Arabic"` so Arabic renders correctly
when the font is installed (DejaVu Sans, the fallback, also covers basic Arabic).

## Color themes

### Dark theme

```css
body { background: #1a1a2e; color: #e0e0e0; }
h1, h2, h3 { color: #8be9fd; }
pre { background: #282a36; }
blockquote { background: #2a2a3e; border-left-color: #bd93f9; color: #cdd6f4; }
table th { background: #44475a; }
```

### Minimal / print-friendly

```css
body { font-family: Georgia, serif; font-size: 11pt; color: #000; }
h1, h2 { color: #000; border-color: #000; }
a { color: #000; text-decoration: underline; }
```

## Code highlighting

If `pygments` is installed, the script auto-enables the `codehilite` extension.
Add highlight CSS to color tokens:

```css
.codehilite .k { color: #ff79c6; }  /* keyword */
.codehilite .s { color: #f1fa8c; }  /* string */
.codehilite .c { color: #6272a4; font-style: italic; }  /* comment */
.codehilite .n { color: #e6e8ee; }  /* name */
```

## Page break control

Prevent awkward breaks:

```css
h1, h2, h3, h4 { page-break-after: avoid; }      /* don't orphan a heading */
table, pre, blockquote { page-break-inside: avoid; } /* don't split these */
```

Force a page break in markdown via raw HTML:

```markdown
<div style="page-break-after: always;"></div>
```

## Tables

Wide tables can overflow. The default CSS uses `width: 100%` with wrapping.
For very wide tables, reduce font size:

```css
table { font-size: 8.5pt; }
td, th { padding: 4px 6px; }
```

## Font availability

WeasyPrint uses system fonts. Common available fonts in Linux containers:

| Font | Good for |
|---|---|
| DejaVu Sans | Latin, basic Arabic, monospace |
| Noto Sans | Latin, CJK |
| Noto Sans Arabic | Arabic (install: `apt install fonts-noto` or `fonts-noto-core`) |
| Liberation Sans | Latin (metric-compatible with Arial) |

To check available fonts: `fc-list | grep -i noto`

## Generating a custom CSS file

Save any CSS above to a file (e.g. `dark.css`) and pass it:

```bash
python .agents/skills/create-pdf/scripts/build_pdf.py input.md --css dark.css -o output.pdf
```
