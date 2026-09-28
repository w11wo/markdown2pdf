# markdown2pdf

GitHub Action that converts your repository's root `README.md` (with images/figures) to a styled PDF using
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
```

After each push: **Actions** tab → latest run → **Artifacts** → `pdfs` → `README.pdf`.
Missing images show up as warnings on the run summary. The run fails if there is no `README.md`
in the repository root (any capitalisation, e.g. `readme.md`, works).

## Inputs

| Input | Default | Description |
|---|---|---|
| `output-dir` | `pdf` | Folder for `README.pdf`; `.` = repository root |
| `page-size` | `A4` | CSS page size, e.g. `Letter`, `A4 landscape` |
| `font-size` | `11` | Base font size (pt) |
| `number-figures` | `true` | "Figure N." caption prefix |
| `css` | | Extra CSS file |
| `upload-artifact` | `true` | Upload `README.pdf` as an artifact |
| `artifact-name` | `pdfs` | Artifact name |

## Markdown features

- **Images / figures**: `![Caption](images/fig1.png)` is resolved relative to the repository root,
  then by filename anywhere in the repo. Remote `https://` images also work.
- A paragraph containing a single image becomes a figure with a numbered caption from the alt text.
- Resize images with attribute lists: `![Caption](fig.png){ width=50% }`.
- Tables, fenced code with syntax highlighting, footnotes, task lists, strikethrough.
