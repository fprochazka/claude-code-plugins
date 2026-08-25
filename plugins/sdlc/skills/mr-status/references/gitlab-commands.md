# mr-status — GitLab command recipes

Load the **glab** skill for `glab api` and `glab mr`, and the **glab-discussion** skill for reading review threads. Each recipe takes a host, a repo path and an MR iid.

> **Hazards — read before running:**
>
> 1. **Read comment data through `glab-discussion`.** It dumps every thread to files, it handles pagination, and some environments block the raw notes and discussions endpoints behind a wrapper. Fall back to the raw discussions API (§6) only when the CLI is missing.
> 2. **Pass `--mr-url` to `glab-discussion`.** The `--project` and `--mr-iid` flags can silently resolve the *current branch's* MR instead of the one asked for.
> 3. **The Bash tool may run under `zsh`.** A glob that matches nothing (`"$DIR"/*-review-bot-*.txt` on an MR with no bot threads) aborts the command *before* it runs, so a trailing `2>/dev/null` does not suppress it. Run `setopt NULL_GLOB` once at the start, and append `/dev/null` to every `grep` file list so `grep` never blocks on stdin when a whole class of files is absent. Both are applied below.
> 4. **Pipeline jobs need a separate tool.** `head_pipeline.status` (§2) is all this skill needs by default. When a red pipeline has to name its failing job, use the `glab-pipeline` skill.

## Setup per MR

```bash
HOST="git.example.com"                 # carry per MR — a set can span hosts
REPO="group/service"                   # carry per MR — do not assume the current directory
IID=4711
ENC="${REPO//\//%2F}"                  # url-encoded repo path for glab api
URL="https://$HOST/$REPO/-/merge_requests/$IID"
```

## 1. Metadata, draft, author, branches, size

```bash
glab mr view "$IID" -R "$REPO" -F json \
  | jq '{iid, title, author: .author.username, source_branch, target_branch,
         draft, work_in_progress, state, created_at, updated_at,
         approvals_required: .approvals_before_merge, changes_count, description}'
```

Diff size — added and removed lines, plus the file count:

```bash
glab mr diff "$IID" -R "$REPO" 2>/dev/null \
  | awk '/^\+/&&!/^\+\+\+/{a++} /^-/&&!/^---/{d++} END{printf "+%d/-%d\n", a, d}'
glab api "projects/$ENC/merge_requests/$IID/changes" | jq '.changes | length'
```

## 2. Rebase state, mergeability, pipeline, approvals

```bash
glab api "projects/$ENC/merge_requests/$IID?include_diverged_commits_count=true&include_rebase_in_progress=true" \
  | jq '{diverged_commits_count, rebase_in_progress,
         merge_status, detailed_merge_status, has_conflicts,
         pipeline: .head_pipeline.status, pipeline_sha: .head_pipeline.sha, head_sha: .sha}'
glab api "projects/$ENC/merge_requests/$IID/approvals" \
  | jq '{approved_by: [.approved_by[].user.username], approvals_left}'
```

- `diverged_commits_count == 0` means up to date. A value above zero means behind by that many commits. This is a snapshot, the target branch keeps moving.
- `detailed_merge_status` says *why* the MR cannot merge: `ci_still_running`, `discussions_not_resolved`, `draft_status`, `conflict`, `not_approved`, and others.
- `pipeline` is the head pipeline verdict. **Only `success` counts as green.** Compare `pipeline_sha` with `head_sha` — a verdict from a superseded head says nothing about the current one.
- An MR that is behind the target branch ran its pipeline against an old base. Judge its CI again after the rebase, not before.

## 3. Dump the review threads

```bash
setopt NULL_GLOB 2>/dev/null || shopt -s nullglob 2>/dev/null
glab-discussion read --mr-url "$URL" --dump      # one .txt per thread + .meta.json
DIR="/tmp/glab-discussion/$HOST/mr-$IID"
```

The dump holds one file per discussion thread, named `<ISO-ts>-<author-slug>-<shortid>.txt` and therefore sorted chronologically by filename. `.meta.json` maps each discussion id to `{max_timestamp, filename}`.

Thread file header:

```
Discussion: <full-id>
Type: General | DiffNote           # DiffNote = inline finding, General = summary or plain comment
Resolved: yes | no                 # PRESENT only on a resolvable thread, ABSENT on a plain comment
URL: <note url>
---
[<ts>] @<username> [BOT] (note:<id>):
<body...>
```

Author identity comes from the filename slug and from the `@username` line. A username maps to its slug by replacing `.` with `-`, so `jane.doe` becomes `jane-doe`.

## 4. Discover who reviewed — identities before verdicts

List every distinct thread author on the MR, and which of them carry a bot marker:

```bash
ls -1 "$DIR"/*.txt 2>/dev/null | xargs -r -n1 basename \
  | sed -E 's/^[0-9T:.-]+-(.+)-[0-9a-f]+\.txt$/\1/' | sort | uniq -c | sort -rn
grep -hoE '@[A-Za-z0-9._-]+ \[BOT\]' "$DIR"/*.txt /dev/null 2>/dev/null | sort -u
```

Take the observed strings as they are. A service account can have an opaque hash for a username, and `author.bot` is not reliably set on every install, so `author.name` and the `[BOT]` marker are often the only usable handles. Confirm the exact string per run instead of hardcoding it.

## 5. Per-reviewer verdict and unresolved count

Set `SLUG` to one author slug from §4, then read newest-first and stop at the first note that carries a real verdict. Acknowledgements and "review skipped" notes are not verdicts, so walk past them:

```bash
SLUG="qa-review-bot"                                     # fictional — use a slug observed in §4
ls -1 "$DIR"/*"$SLUG"*.txt 2>/dev/null | sort -r | head -5 \
  | while read -r f; do echo "=== $(basename "$f")"; sed -n '1,60p' "$f"; done
```

Count the threads by that reviewer that are **currently unresolved**. This is the number that matters, never the count of notes it ever posted:

```bash
grep -lE '^Resolved: no$' "$DIR"/*"$SLUG"*.txt /dev/null 2>/dev/null | wc -l
```

`Resolved:` appears only on a resolvable thread. A plain General comment has no such line. Do not read its absence as "unresolved".

Whether a reply clears a finding depends on the reviewer. Some read replies and resolve their own threads, and an unresolved thread with a substantive reply is then an active dialogue. Others never read replies, and a finding clears only when the code changes and a human resolves the thread. Derive this per reviewer, as SKILL.md describes, and record it.

## 6. Human review

Human threads are the ones whose slug belongs to no AI reviewer identity found in §4. Separate the MR author's own threads, because an author's acceptance report is not review:

```bash
AUTHOR=$(glab mr view "$IID" -R "$REPO" -F json | jq -r '.author.username' | tr '.' '-')
BOTS='qa-review-bot|another-bot'                          # slugs observed in §4, joined by |

for f in $(ls "$DIR"/*.txt 2>/dev/null | grep -vE "$BOTS"); do
  slug=$(basename "$f" | sed -E 's/^[0-9T:.-]+-(.+)-[0-9a-f]+\.txt$/\1/')
  res=$(grep -m1 -oE '^Resolved: (yes|no)' "$f" | awk '{print $2}'); res=${res:-n/a}
  who=reviewer; [ "$slug" = "$AUTHOR" ] && who=author
  echo "$slug  resolved=$res  $who  $(basename "$f")"
done
```

Report the totals: human threads, unresolved ones, reviewer threads against author threads. Human approvals come from §2, not from this list.

Fallback when `glab-discussion` is not installed — one line per thread from the raw API:

```bash
glab api --paginate "projects/$ENC/merge_requests/$IID/discussions?per_page=100" \
  | jq -r '.[] | [ (.notes[0].author.username), (.notes[0].type // "Comment"),
                   ([.notes[] | select(.resolvable)] | if length == 0 then "n/a"
                     else (if (map(.resolved) | all) then "yes" else "no" end) end) ] | @tsv'
```

## Notes

- `glab-discussion read --dump` fetches every thread and updates the dump incrementally on a re-run. `--full` forces a rewrite. Re-run it at the start of every refresh so the dump is current.
- Stay economical. Grep the header lines and the filenames. Read a full body only to get the verdict text out of it.
