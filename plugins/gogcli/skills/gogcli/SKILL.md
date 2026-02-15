---
name: gogcli
description: CLI for querying Google Workspace and consumer Google services (Gmail, Calendar, Drive, Docs, Sheets, Slides, Contacts, Tasks, Forms, Chat, People, Apps Script). Use when working with Google services to search email, manage calendar events, upload/download Drive files, read/write Sheets, send emails, manage contacts or tasks, or any Google API operation from the terminal. Triggered by requests involving Google data, Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, or Google Tasks.
trigger-keywords: google, gmail, email, calendar, drive, docs, sheets, slides, contacts, tasks, forms, gog, gogcli
allowed-tools: Bash(gog auth list:*), Bash(gog auth alias list:*), Bash(gog auth status:*), Bash(gog gmail search:*), Bash(gog gmail messages search:*), Bash(gog gmail thread get:*), Bash(gog gmail get:*), Bash(gog gmail url:*), Bash(gog gmail labels list:*), Bash(gog calendar events:*), Bash(gog calendar event:*), Bash(gog calendar get:*), Bash(gog calendar search:*), Bash(gog calendar calendars:*), Bash(gog calendar freebusy:*), Bash(gog calendar conflicts:*), Bash(gog calendar colors:*), Bash(gog drive ls:*), Bash(gog drive search:*), Bash(gog drive get:*), Bash(gog drive download:*), Bash(gog drive url:*), Bash(gog drive permissions:*), Bash(gog docs cat:*), Bash(gog docs info:*), Bash(gog docs list-tabs:*), Bash(gog docs export:*), Bash(gog slides info:*), Bash(gog slides list-slides:*), Bash(gog slides read-slide:*), Bash(gog slides export:*), Bash(gog sheets get:*), Bash(gog sheets metadata:*), Bash(gog sheets notes:*), Bash(gog sheets export:*), Bash(gog forms get:*), Bash(gog forms responses:*), Bash(gog contacts search:*), Bash(gog contacts list:*), Bash(gog contacts get:*), Bash(gog contacts directory:*), Bash(gog contacts other list:*), Bash(gog contacts other search:*), Bash(gog tasks lists:*), Bash(gog tasks list:*), Bash(gog tasks get:*), Bash(gog people:*), Bash(gog config:*)
---

# gogcli

Command-line interface for Google Workspace and consumer Google services. Binary name: `gog`.

## First Step: Check Account

**Run `gog auth list` at the start of every session** to check available accounts:

```bash
gog auth list
```

Account selection:
- `--account <email|alias>` flag on any command
- `GOG_ACCOUNT` environment variable sets default
- If only one account is stored, it is used automatically

List configured aliases:

```bash
gog auth alias list
```

## Flag Placement

**Always place flags after the subcommand**, not between `gog` and the command group. This ensures command prefix matching works correctly for permissions.

```bash
# Correct:
gog gmail search 'is:unread' --account work --json
gog calendar events --today --account personal

# Wrong:
gog --account work gmail search 'is:unread'
```

## Output Modes

```bash
gog gmail search 'newer_than:7d'                         # Rich TTY (colored tables)
gog gmail search 'newer_than:7d' --plain                  # Stable TSV (for piping)
gog gmail search 'newer_than:7d' --json                   # JSON (for scripting)
gog gmail search 'newer_than:7d' --json --results-only    # JSON without envelope
gog gmail search 'newer_than:7d' --json --select=id,subject  # Select fields
```

## Global Flags

| Flag | Description |
|------|-------------|
| `--account` | Account email or alias |
| `--json` | JSON output |
| `--plain` | TSV output |
| `--results-only` | Drop envelope fields in JSON |
| `--select` | Select fields in JSON output |
| `--dry-run` | Print intended actions, don't execute |
| `--force` | Skip confirmations |
| `--no-input` | Never prompt (CI mode) |
| `--verbose` | Debug logging |

## Discovering Flags

This skill covers the most common usage patterns. For full flag details on any command, run `--help`:

```bash
gog gmail send --help
gog calendar create --help
gog drive upload --help
```

## Gmail Search

### Search Threads

```bash
gog gmail search 'newer_than:7d'                     # Last 7 days
gog gmail search 'from:alice@example.com'             # From sender
gog gmail search 'is:unread' --max 20                 # Unread, limit 20
gog gmail search 'has:attachment newer_than:30d'       # With attachments
gog gmail search 'subject:invoice' --all              # All pages
gog gmail search 'in:sent newer_than:1d' --json       # JSON output
gog gmail search 'label:important' --oldest           # Show first message date
gog gmail search 'query' --fail-empty                 # Exit code 3 if no results
```

Key flags: `--max` (default 10), `--all` (all pages), `--fail-empty` (exit code 3 if no results)

### Search Messages (individual messages, not threads)

```bash
gog gmail messages search 'newer_than:7d'             # Message-level results
gog gmail messages search 'from:me' --include-body    # Include message body
gog gmail messages search 'is:unread' --max 50 --json
```

Key additional flag: `--include-body` (includes decoded message body in output)

### Read Thread / Message

```bash
gog gmail thread get <threadId>                       # Full thread with all messages
gog gmail thread get <threadId> --full                 # Show full message bodies
gog gmail thread get <threadId> --download             # Download attachments
gog gmail thread get <threadId> --download --out-dir ./attachments
gog gmail get <messageId>                              # Single message
gog gmail get <messageId> --format metadata            # Metadata only
gog gmail url <threadId>                               # Print Gmail web URL
```

## Calendar Events

### List Events

```bash
gog calendar events                                   # Primary calendar (default)
gog calendar events --today                            # Today only
gog calendar events --tomorrow                         # Tomorrow only
gog calendar events --week                             # This week (Mon-Sun)
gog calendar events --days 3                           # Next 3 days
gog calendar events --from today --to friday           # Relative dates
gog calendar events --from 2025-01-01 --to 2025-01-08 # Absolute dates
gog calendar events --all                              # All calendars
gog calendar events --weekday                          # Include day-of-week columns
gog calendar events <calendarId> --today               # Specific calendar
gog calendar events --query "standup"                  # Free text search
```

Run `gog calendar events --help` for full flag list.

### Search Events

```bash
gog calendar search "meeting" --today
gog calendar search "standup" --days 30
gog calendar search "quarterly" --from 2025-01-01 --to 2025-03-31 --max 50
```

### Get Single Event

```bash
gog calendar event <calendarId> <eventId>
gog calendar event <calendarId> <eventId> --json       # JSON with timezone info
```

### List Calendars

```bash
gog calendar calendars
```

## Drive Search

### List Files

```bash
gog drive ls                                          # Root folder (default max 20)
gog drive ls --parent <folderId>                      # Specific folder
gog drive ls --max 50                                 # More results
gog drive ls --no-all-drives                          # My Drive only (excludes shared)
gog drive ls --query "mimeType='application/pdf'"     # Drive query filter
```

Key flags: `--max` (default 20), `--parent` (folder ID), `--no-all-drives` (My Drive only)

### Search Files

```bash
gog drive search "invoice"                            # Full-text search
gog drive search "budget report" --max 50
gog drive search "mimeType = 'application/pdf'" --raw-query  # Drive query language
gog drive search "quarterly" --no-all-drives          # My Drive only
```

Key flags: `--max` (default 20), `--raw-query` (use Drive query language directly)

### Get / Download

```bash
gog drive get <fileId>                                # File metadata
gog drive download <fileId>                           # Download file
gog drive download <fileId> --out ./file.pdf          # Specify output path
gog drive download <fileId> --format pdf              # Export Google Docs format
gog drive download <fileId> --format docx
gog drive url <fileId>                                # Print web URL
```

Download format options: `pdf`, `csv`, `xlsx`, `pptx`, `txt`, `png`, `docx`

## Command Groups

| Group | Description |
|-------|-------------|
| `gmail` | Gmail operations |
| `calendar` | Google Calendar |
| `drive` | Google Drive |
| `docs` | Google Docs |
| `slides` | Google Slides |
| `sheets` | Google Sheets |
| `forms` | Google Forms |
| `contacts` | Google Contacts |
| `tasks` | Google Tasks |
| `people` | Google People |
| `chat` | Google Chat (Workspace only) |
| `appscript` | Google Apps Script |
| `auth` | Auth and credentials |
| `config` | Configuration |

Always use full command names (e.g. `gog gmail send`, not `gog send`). Always place flags after the full command path (e.g. `gog gmail search 'query' --account work`, not `gog --account work gmail search 'query'`). Run `gog <group> --help` for full subcommand list.

## Additional Resources

### Reference Files

For detailed command references beyond search/read operations, consult:

- **[references/gmail.md](references/gmail.md)** - Send, drafts, labels, thread modify, batch, filters, settings, tracking, watch
- **[references/calendar.md](references/calendar.md)** - Create, update, delete, respond, freebusy, conflicts, team, focus-time, OOO, working-location
- **[references/drive.md](references/drive.md)** - Upload, mkdir, move, rename, delete, share, permissions, copy, comments
- **[references/docs.md](references/docs.md)** - Export, cat (read as text), create, write, insert, find-replace, tabs, comments
- **[references/slides.md](references/slides.md)** - Create, export, add/replace slides, notes
- **[references/sheets.md](references/sheets.md)** - Read, write, append, clear, format, notes, metadata, create, copy, export
- **[references/forms.md](references/forms.md)** - Create forms, get form details, list/get responses
- **[references/contacts.md](references/contacts.md)** - Search, list, create, update, delete contacts, directory, other contacts
- **[references/tasks.md](references/tasks.md)** - Task lists, add, update, done, undo, delete, clear
- **[references/people.md](references/people.md)** - Profile (me), get user, search, relations
- **[references/auth-config.md](references/auth-config.md)** - Auth commands, multi-account, aliases, keyring, service accounts, config, env vars
