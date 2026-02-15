# Calendar - Create, Update & Manage Commands

For listing/searching events, see the main SKILL.md.

## Create Event

```bash
gog calendar create primary --summary "Meeting" --from 2025-01-15T10:00:00Z --to 2025-01-15T11:00:00Z
gog calendar create primary --summary "Team Sync" --from 2025-01-15T14:00:00Z --to 2025-01-15T15:00:00Z \
  --attendees "alice@example.com,bob@example.com" --location "Zoom"
gog calendar create primary --summary "All Day" --from 2025-01-20 --to 2025-01-21 --all-day
gog calendar create primary --summary "Meeting" --from 2025-01-15T10:00:00Z --to 2025-01-15T11:00:00Z \
  --with-meet                                         # Add Google Meet link
gog calendar create primary --summary "Meeting" --from 2025-01-15T10:00:00Z --to 2025-01-15T11:00:00Z \
  --send-updates all                                   # Notify attendees
```

Create flags: `--summary`, `--from`, `--to`, `--description`, `--location`, `--attendees`, `--all-day`, `--rrule`, `--reminder`, `--event-color` (1-11), `--visibility` (default/public/private/confidential), `--transparency` (busy/free), `--send-updates` (all/externalOnly/none), `--guests-can-invite`, `--guests-can-modify`, `--guests-can-see-others`, `--with-meet`, `--source-url`, `--source-title`, `--attachment`, `--private-prop`, `--shared-prop`, `--event-type` (default/focus-time/out-of-office/working-location)

### Recurrence & Reminders

```bash
gog calendar create primary --summary "Payment" \
  --from 2025-02-11T09:00:00-03:00 --to 2025-02-11T09:15:00-03:00 \
  --rrule "RRULE:FREQ=MONTHLY;BYMONTHDAY=11" \
  --reminder "email:3d" --reminder "popup:30m"
```

## Update Event

```bash
gog calendar update primary <eventId> --summary "Updated Meeting"
gog calendar update primary <eventId> --from 2025-01-15T11:00:00Z --to 2025-01-15T12:00:00Z
gog calendar update primary <eventId> --add-attendee "alice@example.com,bob@example.com"
gog calendar update primary <eventId> --attendees "new@example.com"  # Replaces all attendees
gog calendar update primary <eventId> --send-updates all
```

Update flags: same as create plus `--add-attendee` (preserves existing), `--scope` (single/future/all for recurring), `--original-start` (required for scope=single/future). Set empty value to clear a field.

## Delete Event

```bash
gog calendar delete primary <eventId>
gog calendar delete primary <eventId> --force                        # Skip confirmation
gog calendar delete primary <eventId> --send-updates all             # Notify attendees
gog calendar delete primary <eventId> --scope single --original-start 2025-01-15T10:00:00Z
```

Flags: `--scope` (single/future/all), `--original-start`, `--send-updates` (all/externalOnly/none)

## Respond to Invitation

```bash
gog calendar respond primary <eventId> --status accepted
gog calendar respond primary <eventId> --status declined
gog calendar respond primary <eventId> --status tentative
gog calendar respond primary <eventId> --status declined --comment "Can we reschedule?"
```

Flags: `--status` (accepted/declined/tentative/needsAction), `--comment`

## Propose New Time

```bash
gog calendar propose-time primary <eventId>                          # Print URL
gog calendar propose-time primary <eventId> --open                   # Open in browser
gog calendar propose-time primary <eventId> --decline --comment "Can we do 5pm?"
```

Flags: `--open`, `--decline`, `--comment` (implies --decline)

## Free/Busy

```bash
gog calendar freebusy "primary,work@example.com" --from 2025-01-15T00:00:00Z --to 2025-01-16T00:00:00Z
```

Arguments: comma-separated calendar IDs. Flags: `--from`, `--to` (both required, RFC3339)

## Conflicts

```bash
gog calendar conflicts --today
gog calendar conflicts --week
gog calendar conflicts --days 7
gog calendar conflicts --calendars "primary,work@example.com"
```

Flags: `--from`, `--to`, `--today`, `--week`, `--days`, `--week-start`, `--calendars` (default: primary)

## Team Calendar (Workspace)

Requires Cloud Identity API for Google Workspace.

```bash
gog calendar team engineering@company.com --today
gog calendar team engineering@company.com --week
gog calendar team engineering@company.com --freebusy          # Only busy/free blocks (faster)
gog calendar team engineering@company.com --query "standup"   # Filter by title
gog calendar team engineering@company.com --no-dedup          # Show each person's view
```

Flags: `--freebusy`, `--query`/`-q`, `--max` (default 100), `--no-dedup`, `--from`, `--to`, `--today`, `--tomorrow`, `--week`, `--days`, `--week-start`

## Focus Time

```bash
gog calendar focus-time --from 2025-01-15T13:00:00Z --to 2025-01-15T14:00:00Z
gog calendar focus-time --from 2025-01-15T13:00:00Z --to 2025-01-15T14:00:00Z \
  --auto-decline all --chat-status doNotDisturb
```

Flags: `--summary` (default "Focus Time"), `--from`, `--to`, `--auto-decline` (none/all/new, default all), `--decline-message`, `--chat-status` (available/doNotDisturb, default doNotDisturb), `--rrule`

## Out of Office

```bash
gog calendar out-of-office --from 2025-01-20 --to 2025-01-21 --all-day
gog calendar out-of-office --from 2025-01-20T09:00:00Z --to 2025-01-20T17:00:00Z
```

Flags: `--summary` (default "Out of office"), `--from`, `--to`, `--auto-decline` (none/all/new, default all), `--decline-message`, `--all-day`

## Working Location

```bash
gog calendar working-location --type home --from 2025-01-22 --to 2025-01-23
gog calendar working-location --type office --office-label "HQ" --from 2025-01-22 --to 2025-01-23
gog calendar working-location --type custom --custom-label "Café" --from 2025-01-22 --to 2025-01-23
```

Flags: `--type` (home/office/custom, required), `--from`, `--to`, `--office-label`, `--building-id`, `--floor-id`, `--desk-id`, `--custom-label`

## Other

```bash
gog calendar calendars                                # List all calendars
gog calendar acl <calendarId>                         # List access control rules
gog calendar colors                                   # Show available event colors
gog calendar time                                     # Show server time
gog calendar users                                    # List workspace users
```
