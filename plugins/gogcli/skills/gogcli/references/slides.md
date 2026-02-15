# Google Slides

## Info

```bash
gog slides info <presentationId>                      # Presentation metadata
gog slides list-slides <presentationId>               # List all slides with object IDs
gog slides read-slide <presentationId> <slideId>      # Read slide content, notes, images
```

## Export

```bash
gog slides export <presentationId> --format pptx --out ./deck.pptx
gog slides export <presentationId> --format pdf --out ./deck.pdf
```

Flags: `--out`, `--format` (pdf/pptx, default pptx)

## Create

```bash
gog slides create "My Deck"
gog slides create "My Deck" --parent <folderId>
gog slides create "My Deck" --template <presentationId>   # Copy from template
```

Flags: `--parent`, `--template`

### Create from Markdown

```bash
gog slides create-from-markdown "My Deck" --content-file ./slides.md
gog slides create-from-markdown "My Deck" --content "# Slide 1\n\nContent here"
gog slides create-from-markdown "My Deck" --content-file ./slides.md --parent <folderId>
```

Flags: `--content`, `--content-file`, `--parent`, `--debug`

## Copy

```bash
gog slides copy <presentationId> "My Deck Copy"
gog slides copy <presentationId> "My Deck Copy" --parent <folderId>
```

Flags: `--parent`

## Add Slide

```bash
gog slides add-slide <presentationId> ./slide.png
gog slides add-slide <presentationId> ./slide.png --notes "Speaker notes"
gog slides add-slide <presentationId> ./slide.png --notes-file ./notes.txt
gog slides add-slide <presentationId> ./slide.png --before <slideId>    # Insert before
```

Flags: `--notes`, `--notes-file`, `--before` (slide ID; omit to append)

## Replace Slide Image

```bash
gog slides replace-slide <presentationId> <slideId> ./new-slide.png
gog slides replace-slide <presentationId> <slideId> ./new-slide.png --notes "New notes"
```

Flags: `--notes` (omit to preserve, empty string to clear), `--notes-file`

## Update Speaker Notes

```bash
gog slides update-notes <presentationId> <slideId> --notes "Updated notes"
gog slides update-notes <presentationId> <slideId> --notes-file ./notes.txt
gog slides update-notes <presentationId> <slideId> --notes ""            # Clear notes
```

Flags: `--notes`, `--notes-file`

## Delete Slide

```bash
gog slides delete-slide <presentationId> <slideId>
```
