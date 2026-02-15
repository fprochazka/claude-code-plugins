# Gmail - Write, Organize & Admin Commands

For search/read commands, see the main SKILL.md.

## Send Email

```bash
gog gmail send --to a@b.com --subject "Hi" --body "Hello"
gog gmail send --to a@b.com --subject "Hi" --body-file ./message.txt
gog gmail send --to a@b.com --subject "Hi" --body-file -             # Read from stdin
gog gmail send --to a@b.com --subject "Hi" --body "Plain" --body-html "<p>Hello</p>"
gog gmail send --to a@b.com --cc c@d.com --bcc e@f.com --subject "Hi" --body "Hello"
gog gmail send --to a@b.com --subject "Hi" --body "Hello" --attach ./file.pdf
gog gmail send --to a@b.com --subject "Hi" --body "Hello" --from alias@example.com
```

### Reply

```bash
gog gmail send --reply-to-message-id <messageId> --to a@b.com --subject "Re: Hi" --body "Reply"
gog gmail send --reply-to-message-id <messageId> --quote --to a@b.com --subject "Re: Hi" --body "Reply"
gog gmail send --thread-id <threadId> --to a@b.com --subject "Re: Hi" --body "Reply"
gog gmail send --reply-to-message-id <messageId> --reply-all --subject "Re: Hi" --body "Reply"
```

### Tracking

```bash
gog gmail send --to a@b.com --subject "Hi" --body-html "<p>Hello</p>" --track
gog gmail send --to a@b.com,c@d.com --subject "Hi" --body-html "<p>Hello</p>" --track-split
```

`--track` requires exactly 1 recipient and an HTML body (`--body-html` or `--quote`). `--track-split` sends per-recipient tracked messages.

Send flags: `--to`, `--cc`, `--bcc`, `--subject`, `--body`, `--body-file`, `--body-html`, `--reply-to-message-id`, `--thread-id`, `--reply-all`, `--reply-to`, `--attach`, `--from`, `--track`, `--track-split`, `--quote`

## Thread Operations

### Modify Labels on Thread

```bash
gog gmail thread modify <threadId> --add STARRED --remove INBOX       # Archive + star
gog gmail thread modify <threadId> --add IMPORTANT
gog gmail thread modify <threadId> --remove UNREAD
```

Flags: `--add` (comma-separated labels), `--remove` (comma-separated labels)

### List Attachments

```bash
gog gmail thread attachments <threadId>
gog gmail thread attachments <threadId> --download
gog gmail thread attachments <threadId> --download --out-dir ./attachments
```

### Download Single Attachment

```bash
gog gmail attachment <messageId> <attachmentId>
gog gmail attachment <messageId> <attachmentId> --out ./attachment.bin
```

## Labels

```bash
gog gmail labels list
gog gmail labels get INBOX --json                     # Includes message counts
gog gmail labels create "My Label"
gog gmail labels modify <threadId> --add STARRED --remove INBOX
gog gmail labels modify <threadId1> <threadId2> --add "My Label"    # Multiple threads
gog gmail labels delete <labelIdOrName>               # Confirm required (user labels only)
```

## Drafts

```bash
gog gmail drafts list
gog gmail drafts get <draftId>
gog gmail drafts create --subject "Draft" --body "Body"
gog gmail drafts create --to a@b.com --subject "Draft" --body "Body"
gog gmail drafts update <draftId> --subject "Updated" --body "New body"
gog gmail drafts send <draftId>
gog gmail drafts delete <draftId>
```

Draft create/update flags: `--to`, `--cc`, `--bcc`, `--subject`, `--body`, `--body-file`, `--body-html`, `--reply-to-message-id`, `--reply-to`, `--attach`, `--from`

## Batch Operations

```bash
gog gmail batch modify <messageId1> <messageId2> --add STARRED --remove INBOX
gog gmail batch delete <messageId1> <messageId2>      # Permanent delete
```

## Filters

```bash
gog gmail filters list
gog gmail filters get <filterId>
gog gmail filters create --from 'noreply@example.com' --add-label 'Notifications'
gog gmail filters create --from 'alerts@example.com' --archive --mark-read
gog gmail filters create --subject 'invoice' --add-label 'Finance' --star
gog gmail filters create --has-attachment --add-label 'Attachments'
gog gmail filters delete <filterId>
```

Filter create flags: `--from`, `--to`, `--subject`, `--query`, `--has-attachment`, `--add-label`, `--remove-label`, `--archive`, `--mark-read`, `--star`, `--forward`, `--trash`, `--never-spam`, `--important`

## Settings

```bash
# Vacation
gog gmail settings vacation get
gog gmail settings vacation enable --subject "Out of office" --message "..."
gog gmail settings vacation disable

# Forwarding
gog gmail settings forwarding list
gog gmail settings forwarding add --email forward@example.com
gog gmail settings autoforward get
gog gmail settings autoforward enable --email forward@example.com
gog gmail settings autoforward disable

# Send-as
gog gmail settings sendas list
gog gmail settings sendas create --email alias@example.com

# Delegates (Workspace)
gog gmail settings delegates list
gog gmail settings delegates add --email delegate@example.com
gog gmail settings delegates remove --email delegate@example.com
```

## Email Tracking

```bash
gog gmail track setup --worker-url https://gog-email-tracker.<acct>.workers.dev
gog gmail track status
gog gmail track opens <tracking_id>
gog gmail track opens --to recipient@example.com
gog gmail track opens --since 24h
```

## History

```bash
gog gmail history --since <historyId>
gog gmail history --since <historyId> --max 100 --all
```

## Watch (Pub/Sub Push)

```bash
gog gmail watch start --topic projects/<p>/topics/<t> --label INBOX
gog gmail watch status
gog gmail watch renew
gog gmail watch stop
gog gmail watch serve --bind 127.0.0.1 --token <shared> --hook-url http://127.0.0.1:18789/hooks/agent
```
