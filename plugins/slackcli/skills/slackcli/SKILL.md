---
name: slackcli
description: CLI for interacting with Slack workspaces. Use when working with Slack to read messages, list channels, send messages, add reactions, or resolve Slack URLs. Triggered by requests involving Slack data, channel exploration, message searches, or Slack automation.
trigger-keywords: slack, slack message, slack channel, slack dm, slack thread, slack reaction
---

# slackcli

Command-line interface for Slack API operations.

## Workspace Selection (REQUIRED)

**The `--org=<workspace>` option is mandatory for all commands.** You must specify which Slack workspace to use.

If the user hasn't specified a workspace and it's not clear from context, **ask them which workspace to use** before running any commands.

```bash
slack --org=mycompany conversations list  # Specify workspace explicitly
```

To see available workspaces:
```bash
slack config  # Shows configured workspaces in "orgs" section
```

## Global Options

```bash
slack --org=<workspace>  # REQUIRED: Specify which workspace to use
slack --verbose          # Enable debug logging
slack --json             # Output as JSON (available on most commands)
```

## Commands

### List Conversations

```bash
slack conversations list              # All conversations (cached 6h)
slack conversations list --public     # Public channels only
slack conversations list --private    # Private channels only
slack conversations list --dms        # DMs and group DMs only
slack conversations list --member     # Channels you're a member of
slack conversations list --non-member # Channels you're not in
slack conversations list --refresh    # Force cache refresh
```

### Read Messages

```bash
slack messages '#channel'                    # Last 30 days (default)
slack messages '#channel' --today            # Today only
slack messages '#channel' --last-7d          # Last 7 days
slack messages '#channel' --last-30d         # Last 30 days
slack messages '#channel' --since 2024-01-15 # Since specific date
slack messages '#channel' --since 7d --until 3d  # Relative range
slack messages '#channel' --with-threads     # Include thread replies
slack messages '#channel' --reactions=counts # Show reaction counts
slack messages '#channel' --reactions=names  # Show who reacted
slack messages '#channel' -n 50              # Limit to 50 messages
slack messages '#channel' 1234567890.123456  # View specific thread
slack messages C0123456789 --json            # Use channel ID, JSON output
```

### Check Unread

```bash
slack unread        # Channels with unread messages (sorted by count)
slack unread --json
```

### Resolve Slack URLs

```bash
slack resolve 'https://workspace.slack.com/archives/C0123456789/p1234567890123456'
slack resolve 'https://...' --json
```

Extracts workspace from URL automatically.

### Send Messages

```bash
slack send '#channel' "Hello world"
slack send '#channel' --thread 1234567890.123456 "Reply in thread"
echo "Message" | slack send '#channel' --stdin
slack send '#channel' "Message" --json  # Returns message timestamp
```

### Edit Messages

```bash
slack edit '#channel' 1234567890.123456 "Updated message"
slack edit '#channel' 1234567890.123456 "Updated" --json
```

### Delete Messages

```bash
slack delete '#channel' 1234567890.123456         # With confirmation
slack delete '#channel' 1234567890.123456 --force # Skip confirmation
```

### Reactions

```bash
slack react '#channel' 1234567890.123456 thumbsup    # Add reaction
slack react '#channel' 1234567890.123456 :+1:        # Colons stripped
slack unreact '#channel' 1234567890.123456 thumbsup  # Remove reaction
```

## Channel References

Channels can be specified as:
- `#channel-name` - Channel name with hash
- `C0123456789` - Channel ID

## Message Timestamps

Message timestamps (`ts`) are in format `1234567890.123456`. Get them from:
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

Get user/channel IDs from `--json` output.
