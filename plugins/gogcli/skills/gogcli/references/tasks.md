# Google Tasks

## Task Lists

```bash
gog tasks lists list                                  # List all task lists
gog tasks lists create "My Tasks"                     # Create a new list
```

## List Tasks

```bash
gog tasks list <tasklistId>
gog tasks list <tasklistId> --max 50
gog tasks list <tasklistId> --all                     # All pages
gog tasks list <tasklistId> --show-completed          # Include completed
gog tasks list <tasklistId> --show-hidden             # Include hidden
gog tasks list <tasklistId> --due-min 2025-01-01T00:00:00Z --due-max 2025-01-31T23:59:59Z
```

Flags: `--max` (default 20, max 100), `--page`, `--all`, `--fail-empty`, `--show-completed`, `--show-deleted`, `--show-hidden`, `--show-assigned`, `--due-min`, `--due-max`, `--completed-min`, `--completed-max`, `--updated-min`

## Get Task

```bash
gog tasks get <tasklistId> <taskId>
gog tasks get <tasklistId> <taskId> --json
```

## Add Task

```bash
gog tasks add <tasklistId> --title "Task title"
gog tasks add <tasklistId> --title "Task title" --notes "Description" --due 2025-02-01
gog tasks add <tasklistId> --title "Subtask" --parent <parentTaskId>
gog tasks add <tasklistId> --title "After task" --previous <siblingTaskId>
```

### Repeating Tasks

```bash
gog tasks add <tasklistId> --title "Weekly sync" --due 2025-02-01 --repeat weekly --repeat-count 4
gog tasks add <tasklistId> --title "Daily standup" --due 2025-02-01 --repeat daily --repeat-until 2025-02-05
```

Add flags: `--title` (required), `--notes`, `--due` (RFC3339 or YYYY-MM-DD), `--parent`, `--previous`, `--repeat` (daily/weekly/monthly/yearly), `--repeat-count`, `--repeat-until`

Note: Google Tasks treats due dates as date-only; time components may be ignored.

## Update Task

```bash
gog tasks update <tasklistId> <taskId> --title "New title"
gog tasks update <tasklistId> <taskId> --notes "Updated notes"
gog tasks update <tasklistId> <taskId> --due 2025-03-01
gog tasks update <tasklistId> <taskId> --status completed
gog tasks update <tasklistId> <taskId> --due ""        # Clear due date
```

Flags: `--title`, `--notes`, `--due`, `--status` (needsAction/completed)

## Complete / Undo

```bash
gog tasks done <tasklistId> <taskId>                  # Mark completed
gog tasks undo <tasklistId> <taskId>                  # Mark needs action
```

## Delete / Clear

```bash
gog tasks delete <tasklistId> <taskId>
gog tasks clear <tasklistId>                          # Remove all completed tasks
```
