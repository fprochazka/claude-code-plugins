# mr-status — GitLab command recipes

Load the **glab** skill for `glab api` and `glab mr`, and the **glab-discussion** skill for reading review threads. Each recipe takes a host, a repo path and an MR iid.

> **Hazards — read before running:**
>
> 1. **Read comment data through `glab-discussion`.** It dumps every thread to files, it handles pagination, and some environments block the raw notes and discussions endpoints behind a wrapper. Fall back to the raw discussions API (§6) only when the CLI is missing. **If that fallback returns a wrapper rejection, stop and report it.** Do not route around a block by trying another endpoint, another flag, or the web UI.
> 2. **Pass `--mr-url` to `glab-discussion`.** The `--project` and `--mr-iid` flags can silently resolve the *current branch's* MR instead of the one asked for.
> 3. **The Bash tool may run under `zsh`.** A glob that matches nothing (`"$DIR"/*-review-bot-*.txt` on an MR with no bot threads) aborts the command *before* it runs, so a trailing `2>/dev/null` does not suppress it. Run `setopt NULL_GLOB` once at the start, and append `/dev/null` to every `grep` file list so `grep` never blocks on stdin when a whole class of files is absent. Both are applied below.
> 4. **The pipelines endpoint can be blocked too, jobs and pipelines alike.** `head_pipeline.status` comes from the merge-request endpoint (§2) and is not affected, and it is all this skill needs by default. Do not reach for `projects/<enc>/pipelines`. When a red pipeline has to name its failing job, use the `glab-pipeline` skill.

## Setup per MR

```bash
HOST="git.example.com"                 # carry per MR — a set can span hosts
REPO="group/service"                   # carry per MR — do not assume the current directory
IID=4711
ENC="${REPO//\//%2F}"                  # url-encoded repo path for glab api
URL="https://$HOST/$REPO/-/merge_requests/$IID"
```

**Every call below names the host.** `glab mr` takes it inside `-R` as `-R "$HOST/$REPO"`. `glab api` takes it as `--hostname "$HOST"`. A call that omits the host silently hits the default host and returns a wrong answer rather than an error: `glab mr diff` prints an empty diff, and `glab mr view ... | jq .author.username` returns `null`, which then labels every human thread as a reviewer. Shell exports do not survive between tool calls, so do not rely on `GITLAB_HOST` — put the flag on each command.

## 1. Metadata, draft, author, branches, size

```bash
glab mr view "$IID" -R "$HOST/$REPO" -F json \
  | jq '{iid, title, author: .author.username, source_branch, target_branch,
         draft, work_in_progress, state, created_at, updated_at,
         approvals_required: .approvals_before_merge, changes_count, description}'
```

Diff size — added and removed lines, plus the file count:

```bash
glab mr diff "$IID" -R "$HOST/$REPO" \
  | awk '/^\+/&&!/^\+\+\+/{a++} /^-/&&!/^---/{d++} END{printf "+%d/-%d\n", a, d}'
glab api --hostname "$HOST" "projects/$ENC/merge_requests/$IID/changes" | jq '.changes | length'
```

Let the diff command print its errors. A silenced failure reports `+0/-0`, which reads as an empty MR instead of a failed call. Treat `+0/-0` as a failure to investigate, never as a result.

## 2. Rebase state, mergeability, pipeline, approvals

```bash
glab api --hostname "$HOST" \
  "projects/$ENC/merge_requests/$IID?include_diverged_commits_count=true&include_rebase_in_progress=true" \
  | jq '{diverged_commits_count, rebase_in_progress,
         merge_status, detailed_merge_status, has_conflicts,
         pipeline: .head_pipeline.status, pipeline_sha: .head_pipeline.sha, head_sha: .sha}'
glab api --hostname "$HOST" "projects/$ENC/merge_requests/$IID/approvals" \
  | jq '{approved_by: [.approved_by[].user.username], approvals_left}'
```

- `diverged_commits_count == 0` means up to date. A value above zero means behind by that many commits. This is a snapshot, the target branch keeps moving.
- `detailed_merge_status` says *why* the MR cannot merge: `ci_still_running`, `discussions_not_resolved`, `draft_status`, `conflict`, `not_approved`, and others.
- `pipeline` is the head pipeline verdict. **Only `success` counts as green.** Compare `pipeline_sha` with `head_sha` — a verdict from a superseded head says nothing about the current one.
- An MR that is behind the target branch ran its pipeline against an old base. Judge its CI again after the rebase, not before.
- Keep `head_sha` in hand. §5 needs it to check which commit an AI verdict actually reviewed.

## 3. Dump the review threads

```bash
setopt NULL_GLOB 2>/dev/null || shopt -s nullglob 2>/dev/null
glab-discussion read --mr-url "$URL" --dump      # one .txt per thread + .meta.json
DIR="/tmp/glab-discussion/$HOST/mr-$IID"
```

The dump holds one file per discussion thread, named `<ISO-ts>-<author-slug>-<shortid>.txt`.

**The timestamp in the filename is the thread CREATION time, not its last activity.** Sorting the files by name orders the threads by when each one started. A thread that opened first and received a new note a minute ago still sorts first. To order by activity, read `.meta.json`, which maps each discussion id to `{max_timestamp, filename}` — `max_timestamp` is the last-activity time. `.meta.json` starts with a dot, so `ls "$DIR"/*` does not list it. Name it explicitly.

Thread file header:

```
Discussion: <full-id>
Type: General | DiffNote           # DiffNote = inline finding, General = summary or plain comment
File: <path>                       # DiffNote only
Line: <n>                          # DiffNote only
Commit: <sha>                      # DiffNote only
Resolved: yes | no                 # PRESENT only on a resolvable thread, ABSENT on a plain comment
URL: <note url>
---
[<ts>] @<username> [BOT] (note:<id>):
<body...>
```

**Take every author slug from the §4 listing. Never compute one.** A slug does not follow one rule: a human slug usually is the username with `.` replaced by `-`, but a bot slug can be `bot-` plus `author.name`, or the username while `author.name` differs entirely. A computed slug matches nothing and the reviewer then disappears from the report.

## 4. Discover who reviewed — identities before verdicts

List every distinct thread author on the MR, and which of them carry a bot marker:

```bash
ls -1 "$DIR"/*.txt 2>/dev/null | xargs -r -n1 basename \
  | sed -E 's/^[0-9T:.-]+-(.+)-[0-9a-f]+\.txt$/\1/' | sort | uniq -c | sort -rn
grep -hoE '@[A-Za-z0-9._-]+ \[BOT\]' "$DIR"/*.txt /dev/null 2>/dev/null | sort -u
```

**The `[BOT]` marker finds some AI reviewers and misses others.** A reviewer can post through an account that carries no marker at all, so a marker-only search reports an MR as unreviewed while a bot verdict sits in the thread list. Use a second handle: pull the human roles on the MR, then treat every remaining slug as a reviewer to profile.

```bash
glab mr view "$IID" -R "$HOST/$REPO" -F json \
  | jq '{author: .author.username, assignees: [.assignees[]?.username], reviewers: [.reviewers[]?.username]}'
```

Cross-check the slug list against that output and against the approvers from §2. Any slug that is neither the MR author nor an assigned human is an identity to profile, marker or not. Take the observed strings as they are — a service account can have an opaque hash for a username, and `author.bot` is not reliably set on every install. Confirm the exact strings per run instead of hardcoding them.

## 5. Per-reviewer verdict and unresolved count

**A summary lives in a `Type: General` thread. Findings are `DiffNote`s.** A reviewer either edits its summary note in place or appends a new note into the same original thread, so the summary thread is often one of the OLDEST files while it carries the newest verdict. Two habits break here, and both produce a stale verdict that looks current:

- Sorting files by name and taking the newest picks a recent finding thread and drops the summary thread entirely.
- Reading the top of a thread file shows round one of a summary that has since been rewritten several times.

Filter the reviewer's General threads and read the LAST note of each:

```bash
SLUG="qa-review-bot"                                     # fictional — use a slug observed in §4
for f in "$DIR"/*"$SLUG"*.txt; do
  grep -q '^Type: General' "$f" || continue
  echo "--- $(basename "$f")"
  tac "$f" | awk '/^\[[0-9]{4}-/{print; exit} {print}' | tac
done
```

Acknowledgements and "review skipped" notes are not verdicts. When the last note carries none, walk back through the earlier notes of the same thread until one does.

**Check which commit the verdict reviewed.** A verdict that names a superseded head is stale evidence, exactly as a pipeline result on a superseded head is. Pull the commit out of the verdict text and compare it with `head_sha` from §2:

```bash
HEAD_SHA=$(glab api --hostname "$HOST" "projects/$ENC/merge_requests/$IID" | jq -r '.sha')
SUMMARY="$DIR/<the General thread file found above>"
tac "$SUMMARY" | awk '/^\[[0-9]{4}-/{print; exit} {print}' | tac \
  | grep -oE '\b[0-9a-f]{7,40}\b' | sort -u        # commits the verdict names
echo "head: $HEAD_SHA"
```

Report a stale verdict as stale. Do not report it as the current state of the MR.

Count the threads by that reviewer that are **currently unresolved**. This is the number that matters, never the count of notes it ever posted:

```bash
grep -lE '^Resolved: no$' "$DIR"/*"$SLUG"*.txt /dev/null 2>/dev/null | wc -l
```

`Resolved:` appears only on a resolvable thread. A plain General comment has no such line. Do not read its absence as "unresolved".

Whether a reply clears a finding depends on the reviewer. Some read replies and resolve their own threads, and an unresolved thread with a substantive reply is then an active dialogue. Others never read replies, and a finding clears only when the code changes and a human resolves the thread. Derive this per reviewer, as SKILL.md describes, and record it.

## 6. Human review

Human threads are the ones whose slug belongs to no AI reviewer identity found in §4. Separate the MR author's own threads, because an author's acceptance report is not review:

```bash
AUTHOR_SLUG="jane-doe"                                    # match the author against the §4 slug list, do not compute it
BOTS='qa-review-bot|another-bot'                          # slugs observed in §4, joined by |

for f in $(ls "$DIR"/*.txt 2>/dev/null | grep -vE "$BOTS"); do
  slug=$(basename "$f" | sed -E 's/^[0-9T:.-]+-(.+)-[0-9a-f]+\.txt$/\1/')
  res=$(grep -m1 -oE '^Resolved: (yes|no)' "$f" | awk '{print $2}'); res=${res:-n/a}
  who=reviewer; [ "$slug" = "$AUTHOR_SLUG" ] && who=author
  echo "$slug  resolved=$res  $who  $(basename "$f")"
done
```

**That loop classifies by who OPENED each thread, so it misses a human who only replies inside a bot's thread** — often the most substantive review on the MR. Count note authors across every thread file as well:

```bash
grep -hoE '^\[[0-9T:.+-]+\] @[A-Za-z0-9._-]+' "$DIR"/*.txt /dev/null 2>/dev/null \
  | grep -oE '@[A-Za-z0-9._-]+$' | sort | uniq -c | sort -rn
```

Any human in that list who opened no thread still participated. Report the totals: human threads, unresolved ones, reviewer threads against author threads, and humans who only replied. Human approvals come from §2, not from this list.

Fallback when `glab-discussion` is not installed — one line per thread from the raw API. If it returns a wrapper rejection, stop and report it (hazard 1):

```bash
glab api --hostname "$HOST" --paginate "projects/$ENC/merge_requests/$IID/discussions?per_page=100" \
  | jq -r '.[] | [ (.notes[0].author.username), (.notes[0].type // "Comment"),
                   ([.notes[] | select(.resolvable)] | if length == 0 then "n/a"
                     else (if (map(.resolved) | all) then "yes" else "no" end) end) ] | @tsv'
```

## Notes

- `glab-discussion read --dump` fetches every thread and updates the dump incrementally on a re-run. `--full` forces a rewrite. Re-run it at the start of every refresh so the dump is current.
- Stay economical. Grep the header lines and the filenames. Read a full body only to get the verdict text out of it.
