# Creating Cards and Dashboards

## Workflow

1. Create cards individually via `metabase cards import`
2. Create/update dashboard via `metabase dashboards import` referencing existing cards by `card_id`

Cards are always managed separately. Dashboard import only handles the layout/placement.

## Editing Native SQL Cards

When modifying the SQL query of an exported card, **always extract the query to a separate `.sql` file** rather than editing SQL inside JSON. This avoids JSON escaping issues and makes the query readable.

### Extract, Edit, and Re-pack Workflow

```bash
# 1. Export the card
metabase dashboards export 456

# 2. Extract SQL to a .sql file for editing
jq -r '.card.dataset_query.native.query' card-123.json > card-123.sql

# 3. Edit the .sql file with Read/Edit/Write tools

# 4. Pack SQL back into the card JSON and import
jq --rawfile sql card-123.sql '.card.dataset_query.native.query = $sql' card-123.json | \
  metabase cards import --file - --id 123
```

## Creating Native SQL Cards

Use `metabase cards import` with a JSON file. Minimal required fields:

```json
{
  "name": "My Card Name",
  "display": "table",
  "collection_id": 42,
  "dataset_query": {
    "type": "native",
    "native": {
      "query": "SELECT * FROM my_table",
      "template-tags": {}
    },
    "database": 1
  },
  "visualization_settings": {}
}
```

Common `display` values: `table`, `pie`, `bar`, `line`, `scalar`, `row`, `area`.

To update an existing card's query without changing other fields, only `dataset_query` is needed:

```json
{
  "dataset_query": {
    "type": "native",
    "native": {
      "query": "SELECT * FROM my_table",
      "template-tags": {}
    },
    "database": 1
  }
}
```

## Creating Dashboards with Cards

### Step 1: Create cards

```bash
metabase cards import --file card-a.json    # Returns card ID, e.g. 100
metabase cards import --file card-b.json    # Returns card ID, e.g. 101
```

### Step 2: Create dashboard with card placements

Create a dashboard JSON file referencing the cards by ID:

```json
{
  "name": "My Dashboard",
  "description": "Dashboard description",
  "collection_id": 42,
  "dashcards": [
    {
      "card_id": 100,
      "row": 0,
      "col": 0,
      "size_x": 12,
      "size_y": 5,
      "parameter_mappings": [],
      "visualization_settings": {},
      "series": []
    },
    {
      "card_id": 101,
      "row": 0,
      "col": 12,
      "size_x": 12,
      "size_y": 5,
      "parameter_mappings": [],
      "visualization_settings": {},
      "series": []
    }
  ],
  "parameters": []
}
```

```bash
metabase dashboards import --file dashboard.json
```

The file can also be wrapped in an export envelope (`{"export_version": "1.0", "type": "dashboard", "dashboard": {...}}`), which is the format produced by `metabase dashboards export`.

### Layout Grid

- Metabase uses a 24-column grid
- `col`: 0-23, horizontal position
- `row`: vertical position (rows don't have fixed height, they expand)
- `size_x`: width in columns (e.g., 12 = half width, 24 = full width)
- `size_y`: height in grid units (4-5 is typical for a table card)
