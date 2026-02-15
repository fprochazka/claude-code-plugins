# gogcli

Claude Code skill for interacting with Google services using the [gogcli](https://github.com/steipete/gogcli) CLI (`gog`).

## Requirements

- `gog` CLI installed and on PATH
- At least one Google account authenticated via `gog auth add <email>`

## Installation

```bash
claude plugin install gogcli@fprochazka-claude-code-plugins
```

## Permissions

Add the following to `~/.claude/settings.json` to allow `gog` commands without confirmation:

```json
{
  "permissions": {
    "allow": [
      "Bash(gog:*)"
    ]
  }
}
```

## Capabilities

- **Gmail** - search threads/messages, send emails, manage labels/drafts/filters, batch operations, email tracking
- **Calendar** - list/create/update/delete events, check free/busy, respond to invitations, team calendars
- **Drive** - list/search/upload/download files, manage permissions, organize folders
- **Docs** - export, read as text, create, write, find-replace
- **Slides** - create, export, add/replace slides, manage notes
- **Sheets** - read/write/append/format cells, create spreadsheets, export
- **Forms** - create forms, get responses
- **Contacts** - search/create/update contacts, directory lookup
- **Tasks** - manage task lists and tasks
- **People** - profile information, directory search
- **Chat** - list spaces, send messages (Workspace only)
- **Apps Script** - manage projects, run functions
