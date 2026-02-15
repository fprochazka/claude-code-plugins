# markitdown

Skill for converting files to Markdown using [Microsoft's markitdown](https://github.com/microsoft/markitdown) CLI.

## Installation

```bash
claude plugin install markitdown@fprochazka-claude-code-plugins
```

### Prerequisites

Install the `markitdown` CLI:

```bash
uv tool install 'markitdown[all]'
```

Requires Python >= 3.10.

## What It Does

Provides Claude with knowledge of the `markitdown` CLI for converting various file formats to Markdown:

- **Documents**: PDF, DOCX, PPTX, XLSX, XLS
- **Web**: HTML, RSS, Wikipedia, Bing SERP
- **Data**: CSV, JSON, XML
- **Media**: Images (EXIF metadata), Audio (transcription)
- **Other**: ZIP, EPub, Jupyter notebooks, Outlook MSG, YouTube transcripts

## Usage

Ask Claude to convert files:

```
Convert report.pdf to markdown
Extract text from presentation.pptx
```

The skill provides a concise CLI reference with supported formats, options, and common usage patterns.
