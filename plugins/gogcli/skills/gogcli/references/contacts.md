# Google Contacts

## Search

```bash
gog contacts search "Ada"
gog contacts search "john@example.com" --max 10
```

Flags: `--max` (default 50)

## List

```bash
gog contacts list
gog contacts list --max 100
```

Flags: `--max` (default 100), `--page`

## Get

```bash
gog contacts get people/<resourceName>
gog contacts get user@example.com                     # Get by email
```

## Create

```bash
gog contacts create --given "John" --family "Doe" --email "john@example.com" --phone "+1234567890"
gog contacts create --given "Jane"                    # Only given name is required
```

Flags: `--given` (required), `--family`, `--email`, `--phone`

## Update

```bash
gog contacts update people/<resourceName> --given "Jane" --email "jane@example.com"
gog contacts update people/<resourceName> --birthday "1990-05-12" --notes "Met at WWDC"
gog contacts update people/<resourceName> --email ""  # Clear email
```

### Update from JSON

```bash
gog contacts get people/<resourceName> --json | \
  jq '.contact.urls += [{"value":"https://example.com","type":"profile"}]' | \
  gog contacts update people/<resourceName> --from-file -
```

Update flags: `--given`, `--family`, `--email`, `--phone`, `--birthday` (YYYY-MM-DD), `--notes`, `--from-file` (JSON, use `-` for stdin), `--ignore-etag`

## Delete

```bash
gog contacts delete people/<resourceName>
```

## Workspace Directory

Requires Google Workspace.

```bash
gog contacts directory list
gog contacts directory list --max 50
gog contacts directory search "Jane"
```

## Other Contacts

People interacted with but not in contacts.

```bash
gog contacts other list
gog contacts other list --max 50
gog contacts other search "John"
gog contacts other delete <resourceName>
```
