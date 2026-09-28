"""Markdown -> PDF core (WeasyPrint), with image/figure support. Also usable as a CLI."""

import argparse
import base64
import html
import mimetypes
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import markdown
from weasyprint import HTML
from weasyprint.urls import URLFetcher

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}

MD_EXTENSIONS = [
    "extra",  # tables, fenced code, footnotes, attr_list, def lists, abbr
    "sane_lists",
    "toc",
    "pymdownx.tilde",  # ~~strike~~
    "pymdownx.tasklist",
    "pymdownx.highlight",
    "pymdownx.superfences",
]
MD_EXTENSION_CONFIGS = {
    "pymdownx.highlight": {"use_pygments": True, "noclasses": True, "pygments_style": "friendly"},
    "pymdownx.tasklist": {"custom_checkbox": False},
}

BASE_CSS = """
@page {
  size: %(page_size)s;
  margin: 2cm 2cm 2.2cm 2cm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 9pt; color: #888; }
}
html { font-size: %(font_size)spt; }
body { font-family: "DejaVu Sans", "Helvetica", "Arial", sans-serif; line-height: 1.5; color: #222; }
h1, h2, h3, h4, h5, h6 { line-height: 1.25; margin: 1.2em 0 0.5em; page-break-after: avoid; }
h1 { font-size: 2em; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.15em; }
h3 { font-size: 1.25em; }
p, ul, ol, table, pre, blockquote, figure { margin: 0 0 0.9em; }
a { color: #0366d6; text-decoration: none; }
code { font-family: "DejaVu Sans Mono", "Menlo", monospace; font-size: 0.88em;
       background: #f3f4f6; padding: 0.1em 0.3em; border-radius: 3px; }
pre { background: #f6f8fa; padding: 0.8em 1em; border-radius: 5px; overflow: hidden;
      white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 0.85em; }
.highlight { background: #f6f8fa; border-radius: 5px; }
blockquote { border-left: 4px solid #ddd; color: #555; padding: 0 1em; margin-left: 0; }
table { border-collapse: collapse; width: 100%%; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.6em; text-align: left; }
th { background: #f3f4f6; }
tr:nth-child(even) td { background: #fafafa; }
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
img { max-width: 100%%; height: auto; }
figure { text-align: center; page-break-inside: avoid; }
figure img { max-height: 18cm; }
figcaption { font-size: 0.9em; color: #555; margin-top: 0.4em; }
figcaption .fig-num { font-weight: bold; }
.task-list-item { list-style: none; margin-left: -1.2em; }
.task-box { font-family: "DejaVu Sans", sans-serif; margin-right: 0.35em; }
.footnote { font-size: 0.85em; }
"""

def safe_extract(zip_path: Path, dest: Path) -> None:
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest / member.filename).resolve()
            if not target.is_relative_to(dest):
                raise ValueError(f"Unsafe path in zip: {member.filename}")
            if member.filename.startswith("__MACOSX/"):
                continue
            zf.extract(member, dest)


def _resolve_image(src: str, base_dir: Path, workdir: Path, index: dict) -> Path | None:
    """Find a local image by relative path, falling back to a basename match."""
    if re.match(r"^(https?:|data:)", src):
        return None
    rel = src.split("#")[0].split("?")[0]
    for root in (base_dir, workdir):
        candidate = (root / rel).resolve()
        if candidate.is_relative_to(workdir.resolve()) and candidate.is_file():
            return candidate
    if not index:
        index.update(
            (p.name.lower(), p)
            for p in workdir.rglob("*")
            if p.suffix.lower() in IMAGE_EXTS and not any(part.startswith(".") for part in p.parts)
        )
    return index.get(Path(rel).name.lower())


def _to_data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _process_images(body: str, base_dir: Path, workdir: Path, number_figures: bool):
    """Inline local images as data URIs and wrap standalone images in <figure>."""
    index = {}  # filename -> path, built lazily on first unresolved image
    missing = []

    def replace_src(m):
        src = html.unescape(m.group(3))
        path = _resolve_image(src, base_dir, workdir, index)
        if path is not None:
            return f'{m.group(1)}"{_to_data_uri(path)}"'
        if not re.match(r"^(https?:|data:)", src):
            missing.append(src)
        return m.group(0)

    body = re.sub(r"""(<img\b[^>]*?\bsrc=)(["'])(.*?)\2""", replace_src, body)

    counter = {"n": 0}

    def to_figure(m):
        img = m.group(1)
        alt = re.search(r'\balt="([^"]*)"', img)
        caption = alt.group(1) if alt else ""
        if not caption:
            return f"<figure>{img}</figure>"
        counter["n"] += 1
        label = f'<span class="fig-num">Figure {counter["n"]}.</span> ' if number_figures else ""
        return f"<figure>{img}<figcaption>{label}{caption}</figcaption></figure>"

    # A paragraph containing only one image (optionally wrapped in a link) becomes a figure.
    body = re.sub(r"<p>\s*((?:<a\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</a>)?)\s*</p>", to_figure, body)
    return body, missing


def render_html(md_text, base_dir, workdir, page_size, font_size, number_figures, custom_css):
    body = markdown.markdown(md_text, extensions=MD_EXTENSIONS, extension_configs=MD_EXTENSION_CONFIGS)
    body, missing = _process_images(body, base_dir, workdir, number_figures)
    # Form inputs render poorly in print; draw task-list checkboxes as glyphs.
    body = re.sub(
        r"<input\b[^>]*type=\"checkbox\"[^>]*>",
        lambda m: '<span class="task-box">%s</span>' % ("☑" if "checked" in m.group(0) else "☐"),
        body,
    )
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = html.escape(title_match.group(1).strip()) if title_match else "Document"
    css = BASE_CSS % {"page_size": page_size, "font_size": font_size}
    doc = (
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>'
        f"<style>{css}</style><style>{custom_css or ''}</style></head>"
        f"<body>{body}</body></html>"
    )
    return doc, title, missing


def write_pdf(doc: str, pdf_path: Path) -> None:
    # Local images are already inlined as data URIs; never let the renderer read local files.
    fetcher = URLFetcher(timeout=15, allowed_protocols={"data", "http", "https"})
    HTML(string=doc, url_fetcher=fetcher).write_pdf(pdf_path, presentational_hints=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="markdown2pdf",
        description="Convert Markdown (with images/figures) to PDF. "
        "Images are resolved relative to the markdown file, then by filename.",
    )
    parser.add_argument("input", type=Path, help="Markdown file (.md) or .zip bundle")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF (default: <input>.pdf)")
    parser.add_argument("--page-size", default="A4", help='CSS page size, e.g. A4, Letter, "A4 landscape"')
    parser.add_argument("--font-size", type=float, default=11, help="Base font size in pt (default: 11)")
    parser.add_argument("--no-figure-numbers", action="store_true", help="Don't prefix captions with 'Figure N.'")
    parser.add_argument("--css", type=Path, help="Extra CSS file to apply")
    args = parser.parse_args(argv)

    src = args.input
    if not src.is_file():
        parser.error(f"File not found: {src}")

    tmpdir = None
    if src.suffix.lower() == ".zip":
        tmpdir = Path(tempfile.mkdtemp(prefix="md2pdf_"))
        safe_extract(src, tmpdir)
        candidates = sorted(
            (p for p in tmpdir.rglob("*") if p.suffix.lower() in {".md", ".markdown"}),
            key=lambda p: (len(p.parts), p.name.lower() != "readme.md"),
        )
        if not candidates:
            parser.error(f"No .md file found in {src}")
        md_path, workdir = candidates[0], tmpdir
    else:
        md_path = src
        workdir = src.resolve().parent

    custom_css = args.css.read_text(encoding="utf-8") if args.css else ""
    doc, _, missing = render_html(
        md_path.read_text(encoding="utf-8", errors="replace"),
        md_path.resolve().parent,
        workdir,
        args.page_size,
        args.font_size,
        not args.no_figure_numbers,
        custom_css,
    )
    out = args.output or src.with_suffix(".pdf")
    write_pdf(doc, out)
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)

    for m in sorted(set(missing)):
        print(f"warning: image not found: {m}", file=sys.stderr)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
