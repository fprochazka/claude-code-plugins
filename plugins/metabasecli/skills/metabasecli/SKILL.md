---
name: metabasecli
description: CLI for querying Metabase (cards/questions, dashboards, collections, databases, search). Use when working with Metabase to search entities, browse collections, run saved questions, export/import dashboards, explore database metadata, or resolve Metabase URLs. Triggered by requests involving Metabase data, dashboard queries, saved questions, collection browsing, or Metabase automation.
trigger-keywords: metabase, metabase card, metabase question, metabase query, metabase dashboard, metabase collection, metabase database
allowed-tools: Bash(metabase --help), Bash(metabase auth status:*), Bash(metabase search:*), Bash(metabase resolve:*), Bash(metabase databases list:*), Bash(metabase databases get:*), Bash(metabase databases metadata:*), Bash(metabase databases schemas:*), Bash(metabase collections tree:*), Bash(metabase collections get:*), Bash(metabase collections items:*), Bash(metabase cards list:*), Bash(metabase cards get:*), Bash(metabase cards run:*), Bash(metabase dashboards list:*), Bash(metabase dashboards get:*), Bash(metabase dashboards export:*), Bash(metabase dashboards revisions:*)
---

# metabasecli

Command-line interface for Metabase API operations.

## Terminology

- **Cards** = Questions/Queries in the Metabase UI (`metabase cards`, `metabase queries`, `metabase questions` are aliases)
- **Dashboards** = Dashboards
- **Collections** = Collections (folders for organizing cards and dashboards)
- **Databases** = Connected data sources

## Flag Placement

**Always place flags after the full command path**, not between `metabase` and the command group. This ensures command prefix matching works correctly for permissions.

```bash
# Correct:
metabase databases list --profile prod --json
metabase cards run 123 --limit 100

# Wrong:
metabase -p prod databases list
```

## Global Flags

| Flag | Description |
|------|-------------|
| `-p`, `--profile` | Named profile to use (default: "default") |
| `-v`, `--verbose` | Enable verbose output |
| `--json` | JSON output (available on most commands) |

## JSON Output Format

All commands support `--json`. Output wraps as:
- Success: `{"success": true, "data": {...}, "meta": {"timestamp": "...", "api_calls": N}}`
- Error: `{"success": false, "error": {"code": "...", "message": "..."}}`

Error codes: `NOT_FOUND`, `AUTHENTICATION_ERROR`, `SESSION_EXPIRED`, `PERMISSION_DENIED`, `API_ERROR`, `VALIDATION_ERROR`.

## Authentication

```bash
metabase auth status            # Check current auth status
metabase auth login              # Interactive login
metabase auth login --url https://metabase.example.com --method api_key
metabase auth token              # Print session token (for piping)
metabase auth logout             # Clear stored session
```

## Search

```bash
metabase search "revenue"                              # Search all entities
metabase search "revenue" --models card                # Cards only
metabase search "revenue" --models dashboard           # Dashboards only
metabase search "revenue" --collection-id 42           # Within collection
metabase search "revenue" --database-id 1              # Filter by database
metabase search "revenue" --archived                   # Search archived items
metabase search "revenue" --created-by 5               # By creator user ID
metabase search "revenue" --limit 10                   # Limit results (default 50)
```

Valid `--models` values: `card`, `dashboard`, `collection`, `database`, `table`, `dataset`, `segment`, `metric`, `action`.

## Resolve URLs

Parse Metabase URLs into entity details:

```bash
metabase resolve 'https://metabase.example.com/question/123'
metabase resolve 'https://metabase.example.com/dashboard/456-my-dashboard'
metabase resolve '/collection/789'
metabase resolve '/browse/databases/1'
```

## Databases

```bash
metabase databases list                                # List all databases
metabase databases list --include-tables               # Include table info
metabase databases get 1                               # Database details
metabase databases get 1 --include-tables              # With tables
metabase databases get 1 --include-fields              # With tables and fields
metabase databases metadata 1                          # Full metadata (all tables and fields)
metabase databases metadata 1 --include-hidden         # Include hidden tables/fields
metabase databases schemas 1                           # List schemas
```

## Collections

### Browse Collections

```bash
metabase collections tree                              # Collection hierarchy
metabase collections tree --search "analytics"         # Filter by name
metabase collections tree --search "analytics" -L 3    # Show 3 levels deep (default 1)
metabase collections tree --include-archived           # Include archived
metabase collections get 42                            # Collection details
metabase collections get root                          # Root collection
metabase collections items 42                          # Items in collection
metabase collections items root                        # Items in root
metabase collections items 42 --models card            # Cards only
metabase collections items 42 --models dashboard       # Dashboards only
metabase collections items 42 --archived               # Archived items
metabase collections items 42 --sort-by last_edited_at --sort-dir desc
```

Valid `--models` for items: `card`, `dashboard`, `collection`, `dataset`, `pulse`.
Valid `--sort-by`: `name`, `last_edited_at`, `last_edited_by`, `model`.

### Manage Collections

```bash
metabase collections create --name "My Collection" --parent-id 42
metabase collections create --name "Top Level" --description "A description"
metabase collections update 42 --name "New Name"
metabase collections update 42 --parent-id 10          # Move to different parent
metabase collections archive 42                        # Archive (soft delete)
```

## Cards (Questions/Queries)

### Browse Cards

```bash
metabase cards list --filter mine                      # My cards
metabase cards list --filter bookmarked                # Bookmarked
metabase cards list --filter archived                  # Archived
metabase cards list --collection-id 42                 # By collection
metabase cards list --filter database --database-id 1  # By database
metabase cards get 123                                 # Full card details with query definition
```

At least one filter is required: `--filter`, `--collection-id`, or `--database-id`.

Valid `--filter`: `mine`, `bookmarked`, `archived`, `database`, `table`, `using_model`.

### Run Cards

Execute a saved question and get results:

```bash
metabase cards run 123                                 # Run card (default limit 2000 rows)
metabase cards run 123 --limit 100                     # Limit rows
metabase cards run 123 --parameters '{"date": "2024-01-01"}'  # With parameters
metabase cards run 123 --json                          # JSON output
```

Results are exported to `/tmp/metabase-<timestamp>/`.

### Import/Export Cards

```bash
metabase cards import --file card.json                 # Create new card from JSON
metabase cards import --file card.json --id 123        # Update existing card
metabase cards import --file card.json --collection-id 42  # Override target collection
metabase cards import --file card.json --database-id 1 # Override target database
cat card.json | metabase cards import --file -          # From stdin
```

For JSON format details and creating cards from scratch, see [references/creating-cards-and-dashboards.md](references/creating-cards-and-dashboards.md).

### Delete Cards

```bash
metabase cards archive 123                             # Archive (soft delete)
metabase cards delete 123                              # Permanent delete (with confirmation)
metabase cards delete 123 --force                      # Skip confirmation
```

## Dashboards

### Browse Dashboards

```bash
metabase dashboards list --collection-id 42            # List in collection (required filter)
metabase dashboards get 456                            # Dashboard with dashcard definitions
metabase dashboards get 456 --include-cards            # Include full card definitions
```

### Export Dashboards

```bash
metabase dashboards export 456                         # Export dashboard + all referenced cards
```

Exports to `/tmp/metabase-<timestamp>/` with:
- `dashboard-456.json` — dashboard layout with dashcard placements (card_id references only)
- `card-<id>.json` — one per referenced card (full card definition for context)

### Import Dashboards

Dashboard import only handles the layout. Cards must already exist — create them first with `metabase cards import`.

```bash
metabase dashboards import --file dashboard.json                  # Create new dashboard
metabase dashboards import --file dashboard.json --id 456         # Update existing
metabase dashboards import --file dashboard.json --collection-id 42  # Override collection
cat dashboard.json | metabase dashboards import --file -          # From stdin
```

For creating cards and dashboards from scratch, see [references/creating-cards-and-dashboards.md](references/creating-cards-and-dashboards.md).

### Revisions

```bash
metabase dashboards revisions 456                      # List revisions
metabase dashboards revert 456 789                     # Revert to revision 789
```

### Delete Dashboards

```bash
metabase dashboards archive 456                        # Archive (soft delete)
metabase dashboards delete 456                         # Permanent delete (with confirmation)
metabase dashboards delete 456 --force                 # Skip confirmation
```
