# Drive - Upload, Organize & Share Commands

For listing/searching/downloading files, see the main SKILL.md.

## Upload

```bash
gog drive upload ./report.pdf
gog drive upload ./report.pdf --parent <folderId>
gog drive upload ./report.pdf --name "Q4 Report.pdf"
gog drive upload ./report.pdf --replace <fileId>           # Replace content (preserves shared link)
gog drive upload ./report.docx --convert                    # Convert to Google Docs format
gog drive upload ./data.csv --convert-to sheet              # Convert to Google Sheets
```

Flags: `--name`, `--parent`, `--replace`, `--mime-type`, `--keep-revision-forever`, `--convert`, `--convert-to` (doc/sheet/slides)

## Copy

```bash
gog drive copy <fileId> "Copy Name"
gog drive copy <fileId> "Copy Name" --parent <folderId>
```

Flags: `--parent`

## Organize

```bash
gog drive mkdir "New Folder"
gog drive mkdir "New Folder" --parent <parentFolderId>
gog drive rename <fileId> "New Name"
gog drive move <fileId> --parent <destinationFolderId>
gog drive delete <fileId>                                   # Move to trash
gog drive delete <fileId> --permanent                       # Permanently delete
gog drive url <fileId>                                      # Print web URL
```

## Permissions

```bash
gog drive permissions <fileId>
gog drive share <fileId> --to user --email user@example.com --role reader
gog drive share <fileId> --to user --email user@example.com --role writer
gog drive share <fileId> --to domain --domain example.com --role reader
gog drive share <fileId> --to anyone --role reader
gog drive share <fileId> --to anyone --role reader --discoverable
gog drive unshare <fileId> <permissionId>
```

Share flags: `--to` (anyone/user/domain), `--email`, `--domain`, `--role` (reader/writer, default reader), `--discoverable`

## Comments

```bash
gog drive comments list <fileId>
gog drive comments get <fileId> <commentId>
gog drive comments create <fileId> "Comment text"
gog drive comments update <fileId> <commentId> "Updated text"
gog drive comments delete <fileId> <commentId>
gog drive comments reply <fileId> <commentId> "Reply text"
```

## Shared Drives

```bash
gog drive drives
gog drive drives --max 100
gog drive drives --query "Engineering"
```

Flags: `--max` (default 100), `--page`, `--all`, `--fail-empty`, `--query`/`-q`
