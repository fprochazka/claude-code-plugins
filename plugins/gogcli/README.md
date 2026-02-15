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

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve read-only commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(gogcli)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows read-only commands (`gmail search`, `calendar events`, `drive ls`, `sheets get`, `contacts search`, etc.) and auth/config commands. Write operations (`gmail send`, `calendar create`, `drive upload`, etc.) require manual approval.

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
