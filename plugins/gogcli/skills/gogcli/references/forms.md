# Google Forms

## Get Form

```bash
gog forms get <formId>
gog forms get <formId> --json
```

## Create Form

```bash
gog forms create --title "Weekly Check-in"
gog forms create --title "Survey" --description "Please fill out this survey"
```

Flags: `--title` (required), `--description`

## Responses

### List Responses

```bash
gog forms responses list <formId>
gog forms responses list <formId> --max 50
gog forms responses list <formId> --filter "timestamp > 2025-01-01T00:00:00Z"
```

Flags: `--max` (default 20), `--page`, `--filter`

### Get Response

```bash
gog forms responses get <formId> <responseId>
gog forms responses get <formId> <responseId> --json
```
