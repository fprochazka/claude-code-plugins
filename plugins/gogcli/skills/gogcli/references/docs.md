# Google Docs

**Important:** `gog docs cat` only works on Google Docs. For Sheets use `gog sheets get`, for Slides use `gog slides read-slide`. If unsure about file type, check with `gog drive get <fileId>` first — the `mimeType` field tells the type.

## Read as Text

```bash
gog docs cat <docId>                                  # Print as plain text
gog docs cat <docId> --max-bytes 10000                # Limit output size
gog docs cat <docId> --tab "Notes"                    # Read specific tab
gog docs cat <docId> --all-tabs                       # Read all tabs with headers
```

Flags: `--max-bytes` (default 2000000, 0=unlimited), `--tab`, `--all-tabs`

## Info & Tabs

```bash
gog docs info <docId>                                 # Doc metadata
gog docs list-tabs <docId>                            # List all tabs
```

## Export

```bash
gog docs export <docId> --format pdf --out ./doc.pdf
gog docs export <docId> --format docx --out ./doc.docx
gog docs export <docId> --format txt --out ./doc.txt
```

Flags: `--out`, `--format` (pdf/docx/txt, default pdf)

## Create

```bash
gog docs create "My Doc"
gog docs create "My Doc" --parent <folderId>
gog docs create "My Doc" --file ./doc.md              # Import markdown
```

Flags: `--parent`, `--file`

## Copy

```bash
gog docs copy <docId> "My Doc Copy"
gog docs copy <docId> "My Doc Copy" --parent <folderId>
```

Flags: `--parent`

## Write Content

```bash
gog docs write <docId> "Hello world"                  # Append text
gog docs write <docId> --file ./content.txt           # Append from file
gog docs write <docId> --file - < ./content.txt       # From stdin
gog docs write <docId> --replace --file ./doc.md      # Replace all content
gog docs write <docId> --replace --markdown --file ./doc.md  # Replace with markdown formatting
```

Flags: `--file`/`-f`, `--replace`, `--markdown` (requires --replace)

## Insert Text

```bash
gog docs insert <docId> "Inserted text"               # Insert at beginning (index 1)
gog docs insert <docId> --index 50 "Inserted text"    # Insert at specific position
gog docs insert <docId> --file ./text.txt              # Insert from file
```

Flags: `--index` (default 1), `--file`/`-f`

## Delete Text Range

```bash
gog docs delete <docId> --start 1 --end 50
```

Flags: `--start` (>= 1), `--end` (> start), both required

## Update Content

```bash
gog docs update <docId> --content "New content"
gog docs update <docId> --content-file ./doc.md --format markdown
gog docs update <docId> --content "More content" --append
```

Flags: `--content`, `--content-file`, `--format` (plain/markdown, default plain), `--append`

## Find and Replace

```bash
gog docs find-replace <docId> "old text" "new text"
gog docs find-replace <docId> "Old" "New" --match-case
```

Flags: `--match-case`

## Comments

```bash
gog docs comments list <docId>
gog docs comments get <docId> <commentId>
gog docs comments add <docId> "Comment text"
gog docs comments reply <docId> <commentId> "Reply text"
gog docs comments resolve <docId> <commentId>
gog docs comments delete <docId> <commentId>
```
