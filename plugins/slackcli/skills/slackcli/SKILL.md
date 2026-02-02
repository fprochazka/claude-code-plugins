---
name: slackcli
description: CLI for interacting with Slack workspaces. Use when working with Slack to read messages, list channels, send messages, search, add reactions, or resolve Slack URLs. Triggered by requests involving Slack data, channel exploration, message searches, or Slack automation.
trigger-keywords: slack, slack message, slack channel, slack dm, slack thread, slack reaction, slack search
allowed-tools: Bash(slack:*)
---

# slackcli

Command-line interface for Slack API operations.

## First Step: Check Configuration

**Run `slack config` at the start of every session** to check workspace setup:

```bash
slack config
```

Check the last line of output:
- `Using org from SLACK_ORG: <name>` → No `--org` needed, commands use this workspace
- `No org selected (use --org or SLACK_ORG)` → Must pass `--org=<workspace>` to every command

The output also shows available workspaces in the "orgs" section.

## Workspace Selection

```bash
# When SLACK_ORG env is set (no --org needed):
slack conversations list

# When no org is selected (--org required):
slack --org=mycompany conversations list
```

If the user hasn't specified a workspace and no default is configured, **ask them which workspace to use** (show the available orgs from `slack config`).

## Global Options

```bash
slack --org=<workspace>  # Specify workspace (required if SLACK_ORG not set)
slack --verbose          # Enable debug logging
slack --json             # Output as JSON (available on most commands)
```

## Conversations

```bash
slack conversations list              # All conversations (cached)
slack conversations list --public     # Public channels only
slack conversations list --private    # Private channels only
slack conversations list --dms        # DMs and group DMs only
slack conversations list --member     # Channels you're a member of
slack conversations list --non-member # Channels you're not in
slack conversations list --refresh    # Force cache refresh
```

## Messages

### List Messages

```bash
slack messages list '#channel'                    # Recent messages (default limit 100)
slack messages list '#channel' --today            # Today only
slack messages list '#channel' --last-7d          # Last 7 days
slack messages list '#channel' --last-30d         # Last 30 days
slack messages list '#channel' --since 2024-01-15 # Since specific date
slack messages list '#channel' --since 7d --until 3d  # Relative range
slack messages list '#channel' --with-threads     # Include thread replies
slack messages list '#channel' --reactions=counts # Show reaction counts
slack messages list '#channel' --reactions=names  # Show who reacted
slack messages list '#channel' -n 50              # Limit to 50 messages
slack messages list '#channel' 1234567890.123456  # View specific thread
slack messages list C0123456789 --json            # Use channel ID, JSON output
```

### Send Messages

Send to channels or DMs. Target can be `#channel`, `@username`, `@email@example.com`, or IDs.

```bash
slack messages send '#channel' "Hello world"
slack messages send '@john.doe' "Hello via DM"
slack messages send '#channel' --thread 1234567890.123456 "Reply in thread"
echo "Message" | slack messages send '#channel' --stdin
slack messages send '#channel' --file ./report.pdf           # Upload file
slack messages send '#channel' "Here's the report" --file ./report.pdf
slack messages send '#channel' "Message" --json              # Returns message timestamp
```

### Edit Messages

```bash
slack messages edit '#channel' 1234567890.123456 "Updated message"
slack messages edit '#channel' 1234567890.123456 "Updated" --json
```

### Delete Messages

```bash
slack messages delete '#channel' 1234567890.123456         # With confirmation
slack messages delete '#channel' 1234567890.123456 --force # Skip confirmation
```

## Search

### Search Messages

```bash
slack search messages "quarterly report"
slack search messages "bug fix" --in '#engineering'
slack search messages "deadline" --from '@john.doe'
slack search messages "meeting" --after 7d
slack search messages "project" --before 2024-01-15 --after 2024-01-01
slack search messages "query" --sort timestamp --sort-dir desc
slack search messages "query" -n 50 --page 2
```

### Search Files

```bash
slack search files "report.pdf"
slack search files "spreadsheet" --in '#finance'
slack search files "presentation" --from '@jane.doe'
slack search files "budget" --after 30d
```

## Users

```bash
slack users list                    # List all users (cached)
slack users list --refresh          # Force refresh
slack users list --bots --deleted   # Include bots and deleted users
slack users search "john"           # Search by name/email
slack users get @john.doe           # Get user details
slack users get john@example.com    # Get by email
slack users get U0123456789         # Get by user ID
```

## Files

Files are downloaded to `/tmp/slackcli-<random>/`.

```bash
slack files download F0ABC123DEF                      # Download by file ID
slack files download 'https://files.slack.com/...'   # Download by URL
slack files download F0ABC123DEF --json               # Output download details as JSON
```

## Reactions

```bash
slack reactions add '#channel' 1234567890.123456 thumbsup    # Add reaction
slack reactions add '#channel' 1234567890.123456 :+1:        # Colons stripped
slack reactions remove '#channel' 1234567890.123456 thumbsup # Remove reaction
```

## Pins

```bash
slack pins list '#channel'                           # List pinned messages
slack pins add '#channel' 1234567890.123456          # Pin a message
slack pins remove '#channel' 1234567890.123456       # Unpin a message
```

## Scheduled Messages

```bash
slack scheduled list                                 # List all scheduled
slack scheduled list '#channel'                      # Filter by channel
slack scheduled create '#channel' "in 1h" "Reminder!"
slack scheduled create '#channel' "in 30m" "Meeting soon"
slack scheduled create '#channel' "tomorrow" "Daily standup"
slack scheduled create '#channel' "tomorrow 9am" "Good morning!"
slack scheduled create '#channel' "2025-02-03 09:00" "Team meeting"
slack scheduled create '#channel' --thread 1234567890.123456 "in 1h" "Reply"
slack scheduled delete S0123456789                   # Delete by scheduled ID
```

## Resolve Slack URLs

```bash
slack resolve 'https://workspace.slack.com/archives/C0123456789/p1234567890123456'
slack resolve 'https://...' --json
```

Extracts workspace from URL automatically.

## References

### Channels
- `#channel-name` - Channel name with hash
- `C0123456789` - Channel ID

### Users
- `@username` - Username with @
- `@email@example.com` - Email with @
- `U0123456789` - User ID

### Message Timestamps

Format: `1234567890.123456`. Get them from:
- `--json` output of any message command
- Thread reply indicator in text output
- Slack URL (the `p` parameter, add decimal before last 6 digits)

## Message Formatting

When composing messages, use Slack's mrkdwn syntax:

| Syntax | Result |
|--------|--------|
| `*bold*` | **bold** |
| `_italic_` | _italic_ |
| `` `code` `` | `code` |
| ` ```code block``` ` | code block |
| `<@U123456>` | @mention user |
| `<#C123456>` | #mention channel |
| `<!here>` | @here |
| `<!channel>` | @channel |
| `<https://url\|text>` | hyperlink |

Get user/channel IDs from `--json` output or `slack users get`.
