# markdown2pdf

GitHub Action that converts Markdown (with images/figures) to styled PDFs using
[WeasyPrint](https://weasyprint.org/).

## Usage

Add `.github/workflows/pdf.yml` to your repo:

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
          files: "**/*.md"   # or e.g. "report.md" / "docs/**/*.md"
```

After each push: **Actions** tab → latest run → **Artifacts** → `pdfs`. Missing images show up as
warnings on the run summary.

## Inputs

| Input | Default | Description |
|---|---|---|
| `files` | `**/*.md` | Whitespace-separated globs |
| `output-dir` | `pdf` | Output folder (mirrors source folders); `.` = next to each `.md` |
| `page-size` | `A4` | CSS page size, e.g. `Letter`, `A4 landscape` |
| `font-size` | `11` | Base font size (pt) |
| `number-figures` | `true` | "Figure N." caption prefix |
| `css` | | Extra CSS file |
| `upload-artifact` | `true` | Upload PDFs as an artifact |
| `artifact-name` | `pdfs` | Artifact name |

## Markdown features

- **Images / figures**: `![Caption](images/fig1.png)` is resolved relative to the markdown file,
  then by filename anywhere under that folder. Remote `https://` images also work.
- A paragraph containing a single image becomes a figure with a numbered caption from the alt text.
- Resize images with attribute lists: `![Caption](fig.png){ width=50% }`.
- Tables, fenced code with syntax highlighting, footnotes, task lists, strikethrough.
