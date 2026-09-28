# markdown2pdf

Command-line tool that converts Markdown (with images/figures) to a styled PDF using
[WeasyPrint](https://weasyprint.org/).

## Usage

```bash
markdown2pdf report.md                  # -> report.pdf
markdown2pdf report.md -o out.pdf --page-size Letter
markdown2pdf bundle.zip                 # .md + image folders zipped together
markdown2pdf report.md --css style.css --font-size 12 --no-figure-numbers
markdown2pdf "docs/**/*.md" -d pdf     # many files -> pdf/ (mirrors folders)
markdown2pdf examples/sample.md         # try it out
```

## Features

- **Images / figures**: `![Caption](images/fig1.png)` is resolved relative to the markdown file,
  then by filename anywhere under that folder. Remote `https://` images also work.
- A paragraph containing a single image becomes a figure with a numbered caption from the alt text.
- Resize images with attribute lists: `![Caption](fig.png){ width=50% }`.
- Tables, fenced code with syntax highlighting, footnotes, task lists, strikethrough.
- Page size, base font size, figure numbering, and custom CSS options.
- Warns about image references that could not be found.

## GitHub Action (for students / other repos)

Add `.github/workflows/pdf.yml` to any repo (see [`examples/student-workflow.yml`](examples/student-workflow.yml)):

```yaml
name: Build PDF
on: [push, workflow_dispatch]
jobs:
  pdf:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: w11wo/markdown2pdf@main
        with:
          files: "**/*.md"
```

After each push: **Actions** tab → latest run → **Artifacts** → `pdfs`. Missing images show up as
warnings on the run summary.

| Input | Default | Description |
|---|---|---|
| `files` | `**/*.md` | Whitespace-separated globs |
| `output-dir` | `pdf` | Output folder (mirrors source folders); `.` = next to each `.md` |
| `page-size` | `A4` | CSS page size |
| `font-size` | `11` | Base font size (pt) |
| `number-figures` | `true` | "Figure N." caption prefix |
| `css` | | Extra CSS file |
| `upload-artifact` | `true` | Upload PDFs as an artifact |
| `artifact-name` | `pdfs` | Artifact name |

## GitHub Codespaces (no local install)

1. Push this folder to a GitHub repo.
2. On the repo page: **Code → Codespaces → Create codespace on main**.
3. Wait ~2 minutes. System libraries (Pango, fonts) and the `markdown2pdf` command install automatically.
4. Run `markdown2pdf` in the terminal. Right-click the PDF in the file explorer → **Download** to save it.

## Local install

```bash
pip install -e .
```

WeasyPrint also needs Pango: `brew install pango` (macOS) or `sudo apt install $(cat packages.txt)` (Debian/Ubuntu).
On macOS with Homebrew you may need `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.
