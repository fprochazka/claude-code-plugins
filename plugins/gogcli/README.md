# gogcli

Claude Code skill for interacting with Google services using the [gogcli](https://github.com/steipete/gogcli) CLI (`gog`).

## Requirements

- `gog` CLI installed and on PATH
- At least one Google account authenticated via `gog auth add <email>`

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install gogcli@fprochazka-claude-code-plugins --scope user
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

## Setting up gog CLI

### 1. Install gog

```bash
# Homebrew
brew install steipete/tap/gogcli

# Or build from source
git clone https://github.com/steipete/gogcli.git
cd gogcli && make
sudo cp ./bin/gog /usr/local/bin/gog
```

### 2. Create OAuth credentials in Google Cloud Console

`gogcli` requires you to bring your own OAuth client — it does not ship a bundled one.

1. Create a project at https://console.cloud.google.com/projectcreate
2. Enable the APIs you need:
   - [Gmail API](https://console.cloud.google.com/apis/api/gmail.googleapis.com)
   - [Calendar API](https://console.cloud.google.com/apis/api/calendar-json.googleapis.com)
   - [Drive API](https://console.cloud.google.com/apis/api/drive.googleapis.com)
   - [People API](https://console.cloud.google.com/apis/api/people.googleapis.com)
   - [Tasks API](https://console.cloud.google.com/apis/api/tasks.googleapis.com)
   - [Sheets API](https://console.cloud.google.com/apis/api/sheets.googleapis.com)
   - [Docs API](https://console.cloud.google.com/apis/api/docs.googleapis.com)
   - [Slides API](https://console.cloud.google.com/apis/api/slides.googleapis.com)
   - [Forms API](https://console.cloud.google.com/apis/api/forms.googleapis.com)
   - [Apps Script API](https://console.cloud.google.com/apis/api/script.googleapis.com)
   - [Chat API](https://console.cloud.google.com/apis/api/chat.googleapis.com) (Workspace only)
3. Configure OAuth consent screen at https://console.cloud.google.com/auth/branding
   - User type: **External** (allows personal, GSuite, and other Workspace accounts)
   - Fill in app name, support email, and developer contact email
4. **Publish the app** at https://console.cloud.google.com/auth/audience
   - Click **Publish App** to move from Testing to Production
   - Do **not** submit for verification — just publish
   - This removes the 7-day token expiry and test-user limits
   - Users will see an "unverified app" warning during auth (click Advanced → Go to app)
5. Create an OAuth client at https://console.cloud.google.com/auth/clients
   - Application type: **Desktop app**
   - Download the JSON file

### 3. Store credentials and authenticate

```bash
# Store OAuth client credentials
gog auth credentials set ~/Downloads/client_secret_XXXXX.json

# Authorize accounts (opens browser for each)
gog auth add you@gmail.com
gog auth add you@company.com

# Verify
gog auth list --check

# Set up aliases (optional)
gog auth alias set personal you@gmail.com
gog auth alias set work you@company.com

# Set timezone
gog config set timezone Europe/Prague
```

During the OAuth flow, click **Advanced** → **Go to \<app name\> (unsafe)** to proceed past the unverified app warning.

### Notes

- **Personal Gmail accounts** work immediately with the unverified Production app
- **Google Workspace accounts** may require an admin to allowlist your OAuth client ID (Admin Console → Security → API controls → Manage Third-Party App Access)
- The unverified Production state supports up to 100 Google accounts (lifetime) — plenty for personal use
- Full OAuth verification requires a CASA security assessment ($500–$75k/year) and is not practical for a personal CLI tool
