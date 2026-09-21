---
name: watch
description: Review the current branch's MR, post the findings, then watch it through the glab:mr-watch agent until every blocker and suggestion is addressed or refuted
argument-hint: [focus area or specific concerns]
disable-model-invocation: true
---

# Watch the MR Until the Review Is Settled

Run a full code review of the current branch's merge request, post it, hand the work back to the author, and then watch it through the watcher agent until every blocking finding and every suggestion has been **addressed in code** or **refuted with a reply**.

**The handshake invariant.** Ready-for-review means the MR is **not draft** AND the ticket is in `REVIEW_STATE`. Back-to-work means the MR is **draft** AND the ticket is in `WORK_STATE`. The two flags always move together. Whoever hands the ball over sets both.

That is what paces this command. After posting a round of findings, hand the work back — ticket to `WORK_STATE`, MR to draft. Only when both flags say ready-for-review again does the next round run. This keeps the review out of work-in-progress instead of commenting on every half-finished push.

```
review → post → ticket to WORK_STATE + MR to draft → [wait]
   → author sets MR ready + ticket to REVIEW_STATE
   → sync the local branch onto the author's new head
   → revisit every open thread, reply, resolve what is settled
   → review the delta, post new findings
   → anything still open? ticket to WORK_STATE + MR to draft, wait again
   → nothing open? leave it ready in REVIEW_STATE and stop
```

This command is the **reviewer** side of an MR. It is the mirror image of `/sdlc:mr-babysit`, which is the **author** side. The distinction matters and is enforced below: this command never edits, commits, pushes, or rebases locally, and never resolves the author's threads.

$ARGUMENTS

## Stance — you are the reviewer, not the author

For the whole lifetime of this command, including every follow-up round:

- **Never change the code.** No `Edit`, no `Write` into the repo, no `git commit`, no `git push`, no local `git rebase`, no `git checkout` of a different branch, no stash. If a finding has an obvious fix, describe it in the comment. Do not apply it.
- **Never resolve a thread the author opened.** You may resolve **your own** finding threads, and only once you have verified in the diff that the finding is genuinely addressed.
- **Never promise anything on the MR.** Comment bodies state findings, facts, verification results, and open questions. They do not say "we will fix", "a follow-up is coming", "this will be improved", or any softer paraphrase. If a fix belongs in the picture, describe it as an option in the comment and raise the commitment question with the user in the conversation instead.

Exactly **two** kinds of write to git are authorized (the MR draft flag and the ticket status are metadata, not code — see the autonomy grant below):

1. The server-side rebase via `glab mr rebase` — Phase 1, once, never repeated.
2. The guarded `git reset --hard` of [the local sync procedure](#the-local-sync-procedure) — after that rebase, and again at the start of every follow-up round. It fast-forwards the checkout onto the author's current head so re-reviews read fresh code. It never runs over a dirty tree or over local-only commits.

Nothing else writes to git. Note what the sync is **not**: it moves the branch pointer to match the remote. It never creates a commit, never pushes, and never changes a line the author did not write.

## Autonomy — scoped grant

These are **pre-authorized** for the duration of this command, and you do not stop mid-pass to ask permission for any of them: posting review comments, replying in threads, resolving your own threads, **un-resolving your own threads**, moving the ticket between `WORK_STATE` and `REVIEW_STATE`, **toggling the MR between draft and ready** (`glab mr update <iid> --draft --yes` and `glab mr update <iid> --ready --yes`), commenting on the ticket, the single Phase 1 server-side rebase, the guarded local sync, spawning and stopping the watcher, and arming or deleting the watchdog cron job. This override is scoped to those operations and ends when the watch ends.

Stop and hand back only for the halt conditions under [Termination](#termination).

## Subagents and waiting

The top-level session is the **orchestrator**. It never sleeps, never polls, and never uses the Monitor tool. **This command has nothing to wait for**: it waits on a human, and a human hands the work back hours later. The waiting is the watcher's job, and the watcher tells you when something moved.

**The watcher is the `glab:mr-watch` agent**, spawned once in Phase 6 with `subagent_type: glab:mr-watch`, in the background. It runs the state script in a loop, interprets every change on the MR, and messages you through `SendMessage` without ending its turn. Its messages are what re-invoke you: a handshake flip, a push, new notes, the pipeline finishing, the MR merging. You never poll the MR yourself after Phase 6; a round still reads threads and code as 7.4 and 7.5 say, but what starts a round is the watcher's message, then the ledger. It is read-only by definition and posts nothing.

**Four things re-invoke you, and nothing else:** a watcher message, the watchdog cron every 30 minutes, the review agents returning during a round, and the user. Between them you are idle.

**The one-shot state read in 0.2** goes through a subagent on `sonnet` whose prompt opens with `First, invoke the glab:mr-status skill to load its usage guidance before running any commands.` It runs the state script once, reports the scorecard and the fields 0.2 names, and ends its turn. Read its result back before acting on it; a subagent that timed out read nothing.

**The review round is the one wide fan-out.** `/code-review:full` runs its review agents in parallel, past the usual ceiling of three subagents at a time. That is deliberate here; leave it as it is.

**Every round runs fresh review agents.** This is the documented exception to preferring a resumed subagent over a new one: an agent that already argued a finding in round 1 would defend it in round 2 instead of reading the new code, and a verdict has to come from a cold read.

## Phase 0 — Setup

### 0.1 Tooling

Invoke the `glab` skill and the `glab-discussion` skill before making any GitLab calls. `glab`, `glab-discussion` and `glab-pipeline` are required; when the state script reports one missing, tell the user which, give the install command `uv tool install glab-discussion glab-pipeline`, and ask before installing.

This command also uses two skills from other plugins: `glab:mr-status` for MR state (0.2, and inside the watcher from Phase 6 on) and `sdlc:team-workflow-identify` for the tracker and its state names (0.4). The glab plugin is a declared dependency. If the sdlc skill is unavailable, say so in one line and resolve the workflow states by listing the tracker's actual state names rather than guessing them.

### 0.2 Identify the MR and its refs

The MR is the one for the branch currently checked out. Spawn the one-shot state-read subagent from [Subagents and waiting](#subagents-and-waiting) to read it through the `glab:mr-status` skill, and record: `iid`, `state`, `draft`, `web_url`, `source_branch`, `target_branch`, `sha`, `head_pipeline.status`, `blocking_discussions_resolved`.

Stop and report if there is no MR for this branch, or if `state` is `merged` or `closed`. This command has nothing to watch in those cases.

**If the MR is already `draft` at invocation, warn and proceed.** A draft MR means the author has not handed the work over, so the review reads code they may still be changing. Say so in one line, then run the initial review anyway — the user asked for it explicitly. From Phase 4 onward the draft flag becomes yours to set, and the gate in 7.2 enforces the invariant for every later round.

### 0.3 Define the review refs

Review what is **on the remote**, not what is in the local working tree. The local checkout may be stale, dirty, or ahead of what the author actually pushed, and a server-side rebase in Phase 1 changes the MR head without touching the local branch.

```bash
git fetch origin "$TARGET_BRANCH" "$SOURCE_BRANCH"
```

Then define, for this command and every phase it delegates to:

- `REVIEW_BASE` = `origin/<target_branch>`
- `REVIEW_HEAD` = `origin/<source_branch>`

Fetching the source branch is safe here **because this command never pushes** — the `--force-with-lease` hazard that makes a source-branch fetch dangerous in `/sdlc:mr-babysit` does not apply to a read-only reviewer.

### 0.4 Resolve the ticket and its workflow states

The watch is paced by the handshake, not by pushes, so resolve the ticket now and fail fast if you cannot.

Invoke the `sdlc:team-workflow-identify` skill and carry its output block for the whole watch, every round included. The watcher gets the same block in its spawn prompt, together with the name of the tracker skill, so it can read the ticket. It names the tracker, the ticket ID pattern, and the `WORK_STATE` / `REVIEW_STATE` names this command moves the ticket between, and it asks the user once when a role has several plausible names. Then load the installed skill that covers the resolved tracker — that skill holds the command syntax, and this command names no tracker CLI of its own.

Take the ticket from the MR title, the branch name, or the MR description, using the ticket pattern from the block. Record the ticket ID and both state names in the ledger.

If the block says `tracker: none`, or no ticket is identifiable, say so and fall back to the **push gate**: the follow-up pass then triggers on the MR being not draft with a new head SHA, instead of on a status change. Everything else in this command is unchanged.

## Phase 1 — Rebase gate (server-side, exactly once)

Check whether the MR is behind its target branch:

```bash
git rev-list --count "$REVIEW_HEAD".."$REVIEW_BASE"
```

If the count is `0`, the MR is up to date — skip to Phase 2.

If the count is `> 0`, first capture the remote tip. The rebase is about to move it, and the local sync afterwards needs to know where it was:

```bash
git rev-parse "$REVIEW_HEAD"            # PRE_REMOTE
```

Then trigger a **server-side** rebase, once:

```bash
glab mr rebase "$IID"
```

`glab mr rebase` calls GitLab's `PUT /projects/:id/merge_requests/:iid/rebase` — the same thing the **Rebase** button in the MR UI does. GitLab performs the rebase on its own runner and force-pushes the source branch itself.

Do **not** pass `--skip-ci`. The review reads the pipeline status, so the rebased head needs a real pipeline.

**Rules for this step:**

- **Exactly one attempt, in the initial run only.** Never retry it, and never repeat it in a follow-up round. If the branch falls behind again later, that is the author's to handle.
- **Never fall back to a local rebase.** Whatever the failure, **do not** rebase locally, do not resolve conflicts, do not push. Record it as a finding for the author and carry on with the review against the un-rebased head. The documented failure modes are all the author's to resolve:
  - **Conflicts** — the API cannot resolve them and returns `merge_error: "Rebase failed. Please rebase locally"`. There is no partial or interactive rebase through this endpoint.
  - **`403 Forbidden`** — you lack push access to the source branch.
  - **Fork without maintainer edits** — an MR from a fork needs "Allow edits from maintainers" enabled by its author, otherwise the rebase is refused.
  - **"Reject unverified users" push rule** — where this rule is active, only the MR author can trigger the rebase, even with push access.
  - **Merge trains** — if the project uses merge trains, the train already rebases. Skip this phase entirely rather than fighting it.
- **Say so in the review if a rebase landed.** A server-side rebase rewrites the commits: it strips GPG/SSH signatures, and with "Prevent approval by users who add commits" enabled it resets existing approvals. Note both in the report when the rebase succeeds — the author needs to know why their approvals vanished.
- The API call is asynchronous. Do **not** sleep or poll in a tight loop waiting for it. Trigger it, then continue straight into Phase 2's context loading (MR description, threads, ticket) — that work takes long enough for the rebase to land. **Before** computing the diff range, check the outcome once:

  ```bash
  glab api "projects/:fullpath/merge_requests/$IID?include_rebase_in_progress=true" | jq '{rebase_in_progress, merge_error, sha}'
  ```

  - `rebase_in_progress: false` and `merge_error: null` → the rebase landed. **Do not trust the `sha` from this response** — GitLab returns a stale `sha` for a moment after the flag flips. Derive the head from git instead: re-run `git fetch origin "$SOURCE_BRANCH"`, take `git rev-parse "$REVIEW_HEAD"`, and record that as the reviewed SHA. Then sync the local branch — see below.
  - `merge_error` is set → the rebase failed. Record the exact message verbatim as a `Blocking` finding titled "MR is behind `<target>` and the server-side rebase failed", quoting the error and stating that the author needs to rebase it. Review the un-rebased head.
  - `rebase_in_progress: true` → check once more after the ticket lookup. If it is still in progress then, review the current head and note in the report that the review ran against the pre-rebase state.

### 1.1 Sync the local branch after a successful rebase

The server-side rebase rewrote the branch, so the local checkout is now on commits that no longer exist upstream. Run the [local sync procedure](#the-local-sync-procedure) with `PREV_REMOTE` = `PRE_REMOTE` before continuing.

## The local sync procedure

Used twice: after the Phase 1 rebase, and at the start of every follow-up round (7.3). Both callers rewrite the local branch onto the current remote head.

It takes one input, **`PREV_REMOTE`** — the remote head as it stood *before* it moved:

- Phase 1 → the SHA captured as `PRE_REMOTE` before triggering the rebase.
- Phase 7.3 → `Last reviewed SHA` from the ledger.

**`git pull` is never correct here.** Both callers follow a history rewrite — a server-side rebase, or the author's own force-push. A pull either refuses or builds a merge commit that pollutes the branch. A `git fetch` alone is not enough either: it moves `origin/<source_branch>` and leaves the local branch untouched. The branch must be reset.

```bash
git fetch origin "$SOURCE_BRANCH"
LOCAL=$(git rev-parse HEAD)
[ "$LOCAL" = "$(git rev-parse "$REVIEW_HEAD")" ] && echo "already in sync — nothing to do"

git status --porcelain                          # guard 1 — must be empty
git branch --show-current                       # guard 2 — must equal $SOURCE_BRANCH
git rev-list --count "$PREV_REMOTE".."$LOCAL"   # guard 3 — must be 0
```

The guards, in order of what they protect:

1. **Clean tree.** A reset over uncommitted work destroys it unrecoverably — there is no reflog for something never committed. This guard never yields.
2. **Right branch.** Never reset a branch that is not the MR source branch.
3. **No local-only commits.** A non-zero count means the local branch holds commits that were never on the remote, so the rewrite could not have carried them. Resetting discards them from the branch. The reflog can recover them, but the decision is not yours.

> Guard 3 compares against `PREV_REMOTE`, **not** against `REVIEW_HEAD`. A rewrite gives every carried-over commit a new SHA, so `REVIEW_HEAD..HEAD` counts the whole branch as local-only and the guard would refuse every single time. Measuring against where the remote *was* asks the real question: did this checkout hold anything the remote did not?

All guards pass → move the local branch onto the remote head:

```bash
git reset --hard "$REVIEW_HEAD"
```

Any guard fails → **do not touch the local branch.** Report it prominently: name the failing guard, say the checkout is behind the MR, and for guard 3 list what would have been discarded (`git log --oneline "$REVIEW_HEAD".."$LOCAL"`). Do not try to rescue the divergence — stash, cherry-pick, and merge are all the user's call, not yours. Carry on with the review regardless, because it reads `REVIEW_HEAD`, not the working tree.

Recovery is always available after a successful reset: `git reflog` holds the previous tip, so `git reset --hard <old-sha>` rewinds it.

## Phase 2 — Full review

Read `${CLAUDE_PLUGIN_ROOT}/skills/full/SKILL.md` and execute it, with these substitutions:

- `REVIEW_BASE` and `REVIEW_HEAD` are already defined by Phase 0.3 above; `full.md` reads the same two names, so its 1.2 definition is skipped.
- Its Phase 1.1 (MR context) is partly done — reuse what Phase 0.2 already fetched instead of re-fetching, but do still load the description, labels, and **all** comment threads.
- Pass `$ARGUMENTS` through as its focus-area argument.

Add any Phase 1 rebase failure to the report's **Blocking** section.

**A head pipeline that is not green is itself a Blocking finding.** Read `head_pipeline.status` on `REVIEW_HEAD`. The accepted-green set is `success` alone, as `glab:mr-status` states — `canceled` ran nothing to completion, `manual` is an unfinished blocking gate, and `skipped` means no pipeline ran for this head. Any other value gets a Blocking finding titled "head pipeline is not green", naming the status, the SHA, and the pipeline URL. Do not diagnose the failure and do not propose the fix — that is the author's side.

**`running` and `pending` are not a verdict, and a head in flight is not reviewable.** Read the pipeline status before the review agents start. If it is still running, do not wait for it: treat the gate as closed for this round, note the pipeline in flight in the one-line report, and let the watcher's `PIPELINE_CHANGED` message start the round — a review of a head that then goes red is a review the author has to redo. On the initial run, skip ahead: write the ledger (Phase 5) with `Last reviewed SHA` empty and spawn the watcher (Phase 6); its pipeline message opens the gate on the same handshake and runs the round then.

## Phase 3 — Post the review

Read `${CLAUDE_PLUGIN_ROOT}/skills/post/SKILL.md` and execute it against the report you just produced. Two additions:

- Anchor inline comments against the SHAs of `REVIEW_HEAD`, not the local branch.
- Every body `post.md` writes ends with `<!-- code-review:post -->`. Replace that line, inline and summary alike, with your own signature, so later passes can recognize your own threads by an exact last-line match:

  ```
  <!-- code-review:watch -->
  ```

## Phase 4 — Hand the work back to the author

Once the comments are posted, set **both** halves of the handshake: move the ticket from `REVIEW_STATE` to `WORK_STATE`, and mark the MR draft.

```bash
glab mr update "$IID" --draft --yes
```

Back-to-work means the MR is draft AND the ticket is in `WORK_STATE`. Setting one and not the other leaves the author reading two contradictory signals, and it leaves the 7.2 gate unable to tell a handover from a stale state.

- Set both **only after** every comment from Phase 3 has actually posted. Work handed back before the findings are visible tells the author nothing.
- Add a short tracker comment naming the MR and pointing at the review summary comment. State the findings count by severity. **Do not promise anything** in it — no "we will re-review", no timelines.
- If the ticket is already in `WORK_STATE`, or the MR is already draft, leave that half alone and note it.
- If the ticket move fails (permissions, a workflow transition the tracker forbids), do not fight it. Record the failure in the ledger, tell the user, and fall back to the **push gate** for this watch. Still set the draft flag — it carries the push gate on its own.

Skip the ticket half entirely when Phase 0.4 found no ticket. The draft half always runs.

## Phase 5 — Build the finding ledger

Write a ledger next to the review report, at `./.claude/review-report/<topic>.watch.md`. Every round re-reads and rewrites this file, so the watch survives context compaction and does not depend on remembering what it posted.

```markdown
# Watch ledger: <branch-name> (MR !<iid>)

- MR: <web_url>
- Target: <target_branch>
- Ticket: <TICKET-ID> (<url>) — gate: ticket-status + draft | draft-only
- Work state: <WORK_STATE> · Review state: <REVIEW_STATE>
- Last reviewed SHA: <sha>
- Last handshake reading: <ready-for-review | back-to-work | half-set> at <UTC timestamp>
- Rounds completed: <n>
- Last movement: <UTC timestamp>
- Last round: <UTC timestamp>
- Watcher: <agent id> · ledger ./.claude/review-report/<topic>.mr-watch.md
- Watchdog cron id: <id>

## Findings

| # | Severity | Title | File:line | Thread id | Status | Evidence |
|---|---|---|---|---|---|---|
| 1 | Blocking | ... | src/a.py:42 | <discussion-id> | open | — |
| 2 | Suggestion | ... | (summary) | <discussion-id> | open | — |
```

`Last movement` is the timestamp of the last thing that actually moved: an author push, a draft toggle either way, a new comment from anyone, or a finding changing status. The first three come from the watcher's messages, the last from your own rounds. The idle cap under [Termination](#termination) reads it.

`Status` is one of `open`, `addressed`, `refuted`, `superseded`. Only `Blocking` and `Suggestion` rows gate termination. Record `Nitpick` and `Positive` rows for completeness, but they never keep the watch alive.

Record each migration safety thread as a row with `Migration safety` in the Severity column and the verdict in the Title. These rows never gate on their own — a `Do not run as written` verdict gates through its matching Blocking row.

## Phase 6 — Spawn the watcher and arm the watchdog

Spawn the watcher **by calling the Agent tool, not by describing it**: `subagent_type: glab:mr-watch`, `run_in_background: true`. If you cannot name its agent id in the ledger, nothing is watching. The prompt:

```
MRs: <web_url> (worktree <path>)
Report: handshake, push, notes, verdict, pipeline finished, merged/closed, idle 4h
Cadence: waiting
Self markers: <!-- code-review:watch -->, <!-- code-review:post -->
Handshake: ready-for-review = not draft and ticket in "<REVIEW_STATE>"; back-to-work = draft and ticket in "<WORK_STATE>"
Ticket: <TICKET-ID> — work state "<WORK_STATE>", review state "<REVIEW_STATE>", terminal states <...>; load the <tracker skill name> skill before reading it
Ledger: ./.claude/review-report/<topic>.mr-watch.md
Reviewed at: <REVIEW_HEAD sha>
```

Omit the `Ticket:` line under the push gate and write the `Handshake:` line on the draft flag alone. `Reviewed at` is the SHA of the round you just posted; the watcher reports a ready-for-review reading on that same head with no new notes as `no push since <sha>`, which is the stale case in 7.2. Send `reviewed at <sha>` again after every round.

Then arm the **watchdog** with `CronCreate`, recurring, every 30 minutes on an off-minute (`cron`: `"7,37 * * * *"`), with a one-sentence plain-text prompt naming the MR `!iid`, the ticket, and the ledger path — never a slash command, which would re-enter this command on every firing. Record both ids in the ledger. The heartbeat proves the watcher is alive; nothing proves it is dead, since a watcher that ran out of context, was killed, or is paused on a permission prompt sends nothing, and no message ever wakes you. The cron is the one clock that fires without it. Each firing checks two things and nothing else: is the watcher alive per `ListAgents`, and is `Last message to parent` under 45 minutes old per the watcher's own ledger — a liveness read, never a substitute for a message. Both hold → say nothing and end the turn. Either fails → message the watcher (a message to an ended agent resumes it) or spawn a fresh one against the ledger, and say so in one line. The watchdog never reads the MR itself and never runs a round.

The progress line comes from the watcher's `HEARTBEAT`: on every heartbeat **write one line to the user, even when nothing changed** — the gate it is waiting on, the count of findings still open, and how long the MR has been idle: "!123 still draft, 2 findings open, idle 1h40m". A watch that says nothing for an hour is a dead watch.

Do **not** warn the user that the cron job is session-only or that it expires after 7 days. They know, and it is not a problem.

Then report the initial pass to the user and end the turn. Do not sleep, poll, or wait for the author.

## Phase 7 — The follow-up round (on a watcher message)

A round starts when the watcher's message says the handshake flipped to ready-for-review — or, when `Last reviewed SHA` is still empty because the initial run found the pipeline in flight, when `PIPELINE_CHANGED` reports a settled status while the last handshake reading is ready-for-review; that round is the initial review, Phases 2 to 5, not 7.3 to 7.6. Every other message is information: update the ledger's `Last movement`, write one line to the user if it changes what they would do, and end the turn. A push while the MR is still draft is not a round. A new note is not a round; you read it in the next round. `STATE_CHANGED` to merged or closed goes to [Termination](#termination).

### 7.1 Re-derive state from the ledger and the message

Do not trust what you believed last round. Re-read the ledger, then take `state`, `draft`, `sha` and the pipeline status from the watcher's scorecard line, and fetch the refs:

```bash
git fetch origin "$TARGET_BRANCH" "$SOURCE_BRANCH"
```

**Pin the round to a SHA.** Set `REVIEW_HEAD` to the head SHA the message names, never to `origin/<source_branch>`: a push can land while the review agents run, and a ref would move under them so that some read the old tree and some the new. A push the watcher reports during a round means "re-review next round", never a ref update. `REVIEW_BASE` stays `origin/<target_branch>`.

### 7.2 The handshake gate

The watcher already read both flags; its `ready-for-review` reading is the gate opening. **Half-set is not ready**, and the watcher reports it as such: a ticket in `REVIEW_STATE` while the MR is still draft is a no-op, exactly as before. Do not comment on the mismatch on the MR, and do not fix it for the author.

**Watch for a stale review state.** If the gate opens but the head SHA still equals `Last reviewed SHA` and the watcher reported no new notes since your last round, the author changed nothing. Do not re-review the same code and do not re-post. Reply once in the summary thread naming the findings still `open`, then hand the work back as in Phase 4 — ticket to `WORK_STATE` and MR to draft — and end the turn.

**Push-gate fallback.** When Phase 0.4 found no ticket, or the Phase 4 ticket move failed, the round starts on the watcher reporting the MR not draft with a head SHA that differs from `Last reviewed SHA`. Otherwise it is a no-op.

### 7.3 Sync the local branch to the author's latest push

The gate has opened, so the author has handed the work back. **Before reading a single line of code, bring the local worktree onto the branch head you are about to review.** A follow-up round that reads a stale checkout reviews code the author already replaced, and every finding it produces is wrong.

Run the [local sync procedure](#the-local-sync-procedure) with `PREV_REMOTE` = `Last reviewed SHA` from the ledger; with `Last reviewed SHA` empty there is no previous round, so use the SHA recorded in 0.3. The author may have force-pushed after their own rebase, so treat history as rewritten and never use `git pull`.

If the sync is refused by a guard, say so loudly in the pass report and continue the round anyway — the review itself reads `REVIEW_HEAD`, so it stays correct. What breaks on a refused sync is any tooling that reads the working tree (a build, a test run, an editor), so the user needs to know the checkout is behind.

### 7.4 Revisit every past thread — this is the core of a follow-up round

**Every round revisits every still-open finding from every previous round, and every one of them gets a reply.** This is not optional and it is not limited to the findings the author happened to mention. A finding you posted in round 1 and never returned to is a finding the author cannot close.

Read all threads with `glab-discussion read --dump`. Then, for **each** ledger row still `open`, verify it against the code at the current `REVIEW_HEAD` and reach a verdict. A finding leaves `open` only on **evidence**, never on the author's assertion alone:

- **addressed** — you read the current code and confirmed the problem is gone. The author's reply saying "fixed" is a pointer to check, not proof. If the reply claims a fix but the code still has the problem, the finding **stays open**, and your reply names the exact line that still shows it.
- **refuted** — the author replied with a substantive reason the finding is wrong, marginal, or out of scope, and you have weighed that reason and accept it. **A reply is mandatory**: a thread the author resolved with no reply, or with an empty or content-free reply ("ok", "done", a thumbs-up), does **not** count as refuted — re-open your assessment and say so in the thread. If you disagree with the author's reasoning, the finding stays `open` and your reply gives the specific counter-argument.
- **superseded** — the code moved on and the finding no longer applies to anything in the diff.
- **still open** — neither fixed nor answered.

**Then act on the verdict, in the thread, in this pass:**

| Verdict | Reply | Resolve |
|---|---|---|
| `addressed` | Confirm what you verified, citing the SHA and the file:line that now satisfies it | **Yes** |
| `refuted` | State that you accept the author's reasoning, and why | **Yes** |
| `superseded` | State that the code moved and the finding no longer applies | **Yes** |
| `still open` | State precisely what is still missing — the line, the case, the counter-argument. Never a bare "still open" | **No** |

- **Resolve only your own threads**, and only on a verdict of `addressed`, `refuted`, or `superseded`. Never resolve a thread the author opened — that is theirs to close.
- **Un-resolve your own thread when it was resolved over a problem that is still there.** A verdict of `still open` on a thread that shows as resolved means somebody closed it without the code satisfying it. Re-open it and reply naming the exact line at `REVIEW_HEAD` that still shows the problem:

  ```bash
  glab-discussion resolve <discussion_id> --unresolve
  ```

  `/sdlc:mr-babysit` replies to a `<!-- code-review:watch -->` thread but never resolves one on its own. You resolve the threads you verified. A watch thread that shows as resolved without a verdict of yours behind it was therefore closed on a **human's decision** — the person resolved it, or told the author agent to. Treat it as such: the un-resolve reply addresses a person who read the finding and judged it done, so it states the evidence and nothing sharper. Un-resolve on evidence only, never to keep a thread alive out of doubt.
- **Never resolve without a reply.** A silently resolved thread destroys the record of why the finding went away.
- **One reply per thread per round.** Do not re-state an unchanged verdict every round — a thread that was `still open` last round and is unchanged this round gets one fresh reply only if the author changed something in it or in the code it points at. Otherwise leave it and let the round's summary comment carry the status.
- Reply bodies state findings and verification results. **They never promise anything** — no "we will re-check", no timelines. End every body with a blank line and `<!-- code-review:watch -->`.

Record the evidence for each transition in the ledger's `Evidence` column: a SHA and file:line for `addressed`, the note id for `refuted`.

### 7.5 Review what the author changed

Compare the MR's current `sha` with `Last reviewed SHA` in the ledger. If they match, the author changed no code this round — skip to 7.6.

**`git diff <last_reviewed_sha>..<new_sha>` is the wrong tool here.** If the author rebased, that diff mixes their edits together with every commit master gained in the meantime, and the author's actual work drowns in unrelated churn. The two questions are separate, so ask them separately.

**First, what the author actually changed.** Establish both fork points, then compare the two patch series with `git range-diff`:

```bash
OLD_BASE=$(git merge-base "$LAST_REVIEWED_SHA" "$REVIEW_BASE")
NEW_BASE=$(git merge-base "$REVIEW_HEAD" "$REVIEW_BASE")

git range-diff "$OLD_BASE".."$LAST_REVIEWED_SHA" "$NEW_BASE".."$REVIEW_HEAD"
```

`range-diff` compares the *patches*, not the trees, so a rebase onto a moved master shows as unchanged commits rather than as a wall of new code. Read its markers:

| Marker | Meaning | Attention |
|---|---|---|
| `=` | Commit carried over, patch identical | None — the rebase moved it, the author did not touch it |
| `!` | Commit reworked — the nested interdiff shows exactly what changed inside it | **This is the author's edit.** Review it |
| `>` | New commit added since last round | Review it in full |
| `<` | Commit dropped or squashed away | Check that dropping it was intended, and that no finding anchored to it is now orphaned |

This works whether or not a rebase happened. With no rebase, `OLD_BASE` equals `NEW_BASE` and the output reduces to the added and reworked commits.

**Second, what master brought in.** A rebase can invalidate the branch without the author touching a line — a changed signature upstream, a renamed column, a new constraint. Read it as its own question:

```bash
git log --oneline "$OLD_BASE".."$NEW_BASE"
git diff --stat "$OLD_BASE".."$NEW_BASE"
```

Skip this when `OLD_BASE` equals `NEW_BASE`. Otherwise skim it for anything that interacts with the files the MR touches, and diff in full only where they overlap. You are not reviewing master — you are checking whether the branch still holds on top of it.

Scope the re-review proportionally, using the agent-selection judgment from `full.md` Phase 3.0. A three-line lint fix does not need eight agents. A new module does. Validate any new findings against the actual code exactly as `full.md` Phase 4.1 requires, and drop what you cannot confirm.

Watch for **fixes that introduce new problems** — a hurried fix for a blocking finding is a common source of fresh bugs, and the `!` interdiffs are where they show up.

Then post the update, following `post.md`:

- Post inline threads for **new** findings only. Never re-post a finding already in the ledger — repeat comments on an unchanged point are noise. A finding still `open` is carried by its existing thread (7.4), not by a new one.
- A migration file the round reworked (a `!` interdiff or a `>` commit touching it) gets a fresh assessment from `review-release`, because the old one describes a statement that no longer exists. Post it as a new thread, reply in the old thread with a pointer to the new one, resolve the old thread, and mark its ledger row `superseded`. A migration the round did not touch keeps its thread untouched.
- Post **one** summary comment for this round, with: the round number, the SHA range reviewed, whether the branch was rebased and onto what, the round's new findings not anchored to the diff, and a status table of every gating finding (`addressed` / `refuted` / `open`).
- Give that comment a `### Coverage` section for this round, in the shape `post.md` Phase 7 uses: the agents run, the agents skipped with a one-line reason, and the count of findings dropped in validation. A round that re-reviewed only part of the delta says which part.
- Add the new findings to the ledger as `open` rows.

### 7.6 Hand the work back, update the ledger, end the pass

If any gating finding is still `open` — carried over or newly found — hand the work back as in Phase 4: ticket to `WORK_STATE` **and** `glab mr update "$IID" --draft --yes`. The ball returns to the author, and the next round waits for them to set both flags to ready-for-review again. Under the push gate, set only the draft flag.

If nothing is left open, set neither flag back: leave the MR ready and the ticket in `REVIEW_STATE`, and go to [Termination](#termination).

Rewrite the ledger with the new statuses, the new `Last reviewed SHA`, the new handshake reading, the round count, and the new `Last movement` and `Last round` timestamps. Message the watcher `acted: hand-back on <mr url> at <UTC timestamp>` and `reviewed at <sha>`, so it does not report your own draft flip and ticket move back to you. Then end the turn. The watcher's next message resumes you.

Report what changed: what the author pushed, which findings moved status, what you posted and resolved.

## Termination

**Stop the watch** — message the watcher `stop`, delete the watchdog cron job with `CronDelete`, write the final ledger, and report — when **every** `Blocking` and `Suggestion` row in the ledger is `addressed`, `refuted`, or `superseded`, each transition has recorded evidence, and each corresponding thread has a reply and is resolved.

Open `Nitpick` rows never keep the watch alive.

On a clean termination: leave the MR **ready** and the ticket in `REVIEW_STATE`, and post one final summary comment on the MR stating that every gating finding is settled, with the outcome per finding. The handshake stays on ready-for-review because the review is what finished, not the merge — the MR is now a human's to approve and merge.

**Also stop early**, stopping the watcher, deleting the watchdog cron job and reporting, on any of:

- the MR is merged or closed;
- the ticket reaches a terminal state (done, cancelled, or equivalent) — the work moved past review;
- the author (or the user) asks you to stop;
- you lose access — `glab` or the tracker starts failing authentication;
- the same finding has bounced between `open` and a claimed fix **three times** without converging. Report it as a stalemate that needs a human conversation, and name it explicitly rather than watching it forever;
- **the idle cap: `Last movement` is more than 4 hours old.** Nobody is working the MR. The watcher reports the cap itself when its own last observed movement crosses it; your `Last movement` also counts a finding changing status, so you may end the watch before the watcher does.

**Leave nothing running.** A stop is complete only when the watcher has acknowledged the stop and ended its turn and the watchdog cron is deleted.

On termination, present a final summary to the user: the MR state, the round count, the per-finding outcome table from the ledger, every finding that was refuted and why you accepted the refutation, and anything you deliberately left to the author (the Phase 1 rebase failure belongs here if it happened). When the idle cap ended it, say so plainly — it **stopped on an idle timeout, not because the review settled** — name what is still open, and name the way back in: running `/code-review:watch` again picks the MR back up.
