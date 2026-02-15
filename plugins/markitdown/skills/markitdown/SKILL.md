---
name: markitdown
description: CLI for converting files to Markdown using Microsoft's markitdown. Use when converting PDF, DOCX, PPTX, XLSX, HTML, images, audio, or other file formats to Markdown for text analysis or LLM processing. Triggered by requests involving file-to-markdown conversion, document text extraction, or preparing files for LLM input.
trigger-keywords: markitdown, convert to markdown, file to markdown, extract text, pdf to markdown, docx to markdown, pptx to markdown, xlsx to markdown
allowed-tools: Bash(markitdown:*)
---

# markitdown

Command-line tool for converting various file formats to Markdown. Built by Microsoft for LLM and text analysis pipelines.

## Basic Usage

```bash
markitdown document.pdf                    # Convert, output to stdout
markitdown document.pdf -o output.md       # Convert, write to file
cat document.pdf | markitdown              # Convert from stdin
markitdown document.pdf > output.md        # Redirect stdout to file
markitdown < document.pdf                  # Redirect stdin
```

## Supported Formats

Converted without any extras: HTML, CSV, JSON, XML, plain text, ZIP (iterates contents), EPub, Jupyter notebooks (.ipynb), RSS feeds, Wikipedia URLs, Bing SERP results.

With extras installed: PDF, DOCX, PPTX, XLSX, XLS, Outlook MSG, images (EXIF metadata + optional LLM captioning), audio (EXIF metadata + optional transcription), YouTube URLs (transcript extraction).

## Options

```bash
markitdown -v                              # Show version
markitdown -o FILE                         # Write output to file instead of stdout
markitdown -x .pdf                         # Hint file extension (useful with stdin)
markitdown -m application/pdf              # Hint MIME type
markitdown -c UTF-8                        # Hint charset
markitdown --keep-data-uris                # Keep base64-encoded data URIs in output (truncated by default)
```

### Azure Document Intelligence

For higher-quality extraction using cloud OCR:

```bash
markitdown -d -e "https://your-endpoint.cognitiveservices.azure.com" document.pdf
```

### Plugins

Third-party plugins extend format support via the `markitdown.plugin` entry point:

```bash
markitdown --list-plugins                  # List installed plugins
markitdown -p document.xyz                 # Enable plugins for conversion
```

## Common Patterns

### Convert a file and pipe to another tool

```bash
markitdown report.pdf | wc -w                       # Word count
markitdown report.pdf | head -50                     # Preview first 50 lines
```

### Batch convert multiple files

```bash
for f in *.pdf; do markitdown "$f" -o "${f%.pdf}.md"; done
```

### Convert from URL (via curl)

```bash
curl -sL "https://example.com/doc.pdf" | markitdown -x .pdf
```

### Convert and process with stdin extension hint

When piping content, provide an extension hint so markitdown can select the right converter:

```bash
cat unknown_file | markitdown -x .docx
```
