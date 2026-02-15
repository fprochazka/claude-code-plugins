# Auth & Config

## Authentication

### Store OAuth Credentials

```bash
gog auth credentials set <path-to-client-secret.json>
gog auth credentials list                             # List stored credentials
gog --client work auth credentials set <path.json>    # Named client
```

### Add Account

```bash
gog auth add <email>                                  # Opens browser for OAuth
gog auth add <email> --services gmail,calendar        # Request specific scopes
gog auth add <email> --services user                  # All user services
gog auth add <email> --readonly                       # Read-only scopes
gog auth add <email> --drive-scope file               # Per-file Drive access
gog auth add <email> --force-consent                  # Force re-consent (gets new refresh token)
gog auth add <email> --manual                         # Manual flow (no browser)
gog auth add <email> --remote --step 1                # Remote flow step 1
gog auth add <email> --remote --step 2 --auth-url '...'  # Remote flow step 2
```

Flags: `--services` (comma-separated: gmail, calendar, chat, classroom, drive, docs, slides, contacts, tasks, sheets, people, forms, appscript, groups, keep), `--readonly`, `--drive-scope` (full/readonly/file), `--force-consent`, `--manual`, `--remote`, `--step`

### List & Verify Accounts

```bash
gog auth list                                         # List stored accounts
gog auth list --check                                 # Validate tokens
gog auth status                                       # Current auth state
gog auth services                                     # List available services and scopes
```

### Remove Account

```bash
gog auth remove <email>
```

### Account Aliases

```bash
gog auth alias list
gog auth alias set <alias> <email>
gog auth alias unset <alias>
```

### Keyring Backend

```bash
gog auth keyring                                      # Show current backend
gog auth keyring file                                 # Use encrypted file
gog auth keyring keychain                             # Use macOS Keychain
gog auth keyring auto                                 # Auto-detect best
```

### Multiple OAuth Clients

```bash
gog --client work auth credentials set <path.json>
gog --client work auth add <email>
```

### Service Accounts (Workspace Only)

```bash
gog auth service-account set <email> --key <path-to-service-account.json>
gog auth service-account status <email>
gog auth service-account unset <email>
```

## Configuration

### Config Commands

```bash
gog config path                                       # Show config file path
gog config list                                       # List all values
gog config keys                                       # List available keys
gog config get <key>                                  # Get a value
gog config set <key> <value>                          # Set a value
gog config unset <key>                                # Remove a value
```

Valid keys: `timezone`, `keyring_backend`

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOG_ACCOUNT` | Default account email or alias |
| `GOG_CLIENT` | OAuth client name |
| `GOG_JSON` | Default JSON output |
| `GOG_PLAIN` | Default plain output |
| `GOG_COLOR` | Color mode: auto, always, never |
| `GOG_TIMEZONE` | Default timezone (IANA name, UTC, or local) |
| `GOG_ENABLE_COMMANDS` | Comma-separated allowlist of top-level commands |
| `GOG_KEYRING_BACKEND` | Force keyring backend (overrides config) |
| `GOG_KEYRING_PASSWORD` | Password for file keyring backend (CI/non-interactive) |

### Config File

Location: `~/.config/gogcli/config.json` (Linux), `~/Library/Application Support/gogcli/config.json` (macOS)

Supports JSON5 (comments, trailing commas).
