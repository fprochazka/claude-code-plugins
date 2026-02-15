# Google People

## Profile

```bash
gog people me                                         # Current user profile
gog people me --json
```

## Get User

```bash
gog people get people/<userId>
gog people get people/<userId> --json
```

## Search (Workspace Directory)

```bash
gog people search "Ada Lovelace"
gog people search "Ada" --max 10
```

Flags: `--max` (default 50), `--page`, `--all`, `--fail-empty`

## Relations

```bash
gog people relations                                  # Current user's relations
gog people relations people/<userId>                  # Specific user's relations
gog people relations people/<userId> --type manager   # Filter by type
```

Flags: `--type` (filter relation type)
