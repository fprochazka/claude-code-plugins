---
description: Review the current branch's MR, post the findings, then watch on a cron until every blocker and suggestion is addressed or refuted
argument-hint: [focus area or specific concerns]
disable-model-invocation: true
---

# Watch the MR Until the Review Is Settled

Run a full code review of the current branch's merge request, post it, hand the work back to the author, and then watch on a schedule until every blocking finding and every suggestion has been **addressed in code** or **refuted with a reply**.

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

For the whole lifetime of this command, including every cron pass:

- **Never change the code.** No `Edit`, no `Write` into the repo, no `git commit`, no `git push`, no local `git rebase`, no `git checkout` of a different branch, no stash. If a finding has an obvious fix, describe it in the comment. Do not apply it.
- **Never resolve a thread the author opened.** You may resolve **your own** finding threads, and only once you have verified in the diff that the finding is genuinely addressed.
- **Never promise anything on the MR.** Comment bodies state findings, facts, verification results, and open questions. They do not say "we will fix", "a follow-up is coming", "this will be improved", or any softer paraphrase. If a fix belongs in the picture, describe it as an option in the comment and raise the commitment question with the user in the conversation instead.

Exactly **two** kinds of write to git are authorized (the MR draft flag and the ticket status are metadata, not code — see the autonomy grant below):

1. The server-side rebase via `glab mr rebase` — Phase 1, once, never repeated.
2. The guarded `git reset --hard` of [the local sync procedure](#the-local-sync-procedure) — after that rebase, and again at the start of every follow-up round. It fast-forwards the checkout onto the author's current head so re-reviews read fresh code. It never runs over a dirty tree or over local-only commits.

Nothing else writes to git. Note what the sync is **not**: it moves the branch pointer to match the remote. It never creates a commit, never pushes, and never changes a line the author did not write.

## Autonomy — scoped grant

These are **pre-authorized** for the duration of this command, and you do not stop mid-pass to ask permission for any of them: posting review comments, replying in threads, resolving your own threads, **un-resolving your own threads**, moving the ticket between `WORK_STATE` and `REVIEW_STATE`, **toggling the MR between draft and ready** (`glab mr update <iid> --draft --yes` and `glab mr update <iid> --ready --yes`), commenting on the ticket, the single Phase 1 server-side rebase, the guarded local sync, and arming or deleting the cron job. This override is scoped to those operations and ends when the watch ends.

Stop and hand back only for the halt conditions under [Termination](#termination).

## Phase 0 — Setup

### 0.1 Tooling

Invoke the `glab` skill and the `glab-discussion` skill before making any GitLab calls. If `glab-discussion` is unavailable, fall back to raw `glab api` calls for discussions (`projects/:id/merge_requests/<iid>/discussions`). If `glab` itself is unavailable, stop and tell the user.

This command also uses two skills from other plugins: `glab:mr-status` for MR state (0.2, 7.1) and `sdlc:team-workflow-identify` for the tracker and its state names (0.4). If either is unavailable, say so in one line and carry the work yourself — read the MR through `glab mr view --output=json`, and resolve the workflow states by listing the tracker's actual state names rather than guessing them.

### 0.2 Identify the MR and its refs

The MR is the one for the branch currently checked out. Invoke the `glab:mr-status` skill to read its state, and record: `iid`, `state`, `draft`, `web_url`, `source_branch`, `target_branch`, `sha`, `head_pipeline.status`, `blocking_discussions_resolved`.

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

Invoke the `sdlc:team-workflow-identify` skill and carry its output block for the whole watch, every cron pass included. It names the tracker, the ticket ID pattern, and the `WORK_STATE` / `REVIEW_STATE` names this command moves the ticket between, and it asks the user once when a role has several plausible names. Then load the installed skill that covers the resolved tracker — that skill holds the command syntax, and this command names no tracker CLI of its own.

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

- **Exactly one attempt, in the initial run only.** Never retry it, and never repeat it in a follow-up cron pass. If the branch falls behind again later, that is the author's to handle.
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

Read `${CLAUDE_PLUGIN_ROOT}/commands/full.md` and execute it, with these substitutions:

- Wherever it says `<base>`, use `REVIEW_BASE`. Wherever it says `HEAD`, use `REVIEW_HEAD`. Pass the range `REVIEW_BASE...REVIEW_HEAD` to the review agents instead of `<base>...HEAD`.
- Its Phase 1.1 (MR context) is partly done — reuse what Phase 0.2 already fetched instead of re-fetching, but do still load the description, labels, and **all** comment threads.
- Pass `$ARGUMENTS` through as its focus-area argument.

Add any Phase 1 rebase failure to the report's **Blocking** section.

**A head pipeline that is not green is itself a Blocking finding.** Read `head_pipeline.status` on `REVIEW_HEAD`. The accepted-green set is `success` alone, as `glab:mr-status` states — `canceled` ran nothing to completion, `manual` is an unfinished blocking gate, and `skipped` means no pipeline ran for this head. Any other value gets a Blocking finding titled "head pipeline is not green", naming the status, the SHA, and the pipeline URL. `running` and `pending` are not a verdict yet: note the pipeline is still in flight and re-check it in the next round rather than filing the finding. Do not diagnose the failure and do not propose the fix — that is the author's side.

## Phase 3 — Post the review

Read `${CLAUDE_PLUGIN_ROOT}/commands/post.md` and execute it against the report you just produced. Two additions:

- Anchor inline comments against the SHAs of `REVIEW_HEAD`, not the local branch.
- Append this line to every comment body you post, inline and summary alike, so later passes can recognize your own threads by an exact last-line match:

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

Write a ledger next to the review report, at `./.claude/review-report/<topic>.watch.md`. Every cron pass re-reads and rewrites this file, so the watch survives context compaction and does not depend on remembering what it posted.

```markdown
# Watch ledger: <branch-name> (MR !<iid>)

- MR: <web_url>
- Target: <target_branch>
- Ticket: <TICKET-ID> (<url>) — gate: ticket-status + draft | draft-only
- Work state: <WORK_STATE> · Review state: <REVIEW_STATE>
- Last reviewed SHA: <sha>
- Last seen ticket state: <state>
- Last seen draft: <yes|no>
- Rounds completed: <n>
- Last pass: <UTC timestamp>
- Cron job id: <id>

## Findings

| # | Severity | Title | File:line | Thread id | Status | Evidence |
|---|---|---|---|---|---|---|
| 1 | Blocking | ... | src/a.py:42 | <discussion-id> | open | — |
| 2 | Suggestion | ... | (summary) | <discussion-id> | open | — |
```

`Status` is one of `open`, `addressed`, `refuted`, `superseded`. Only `Blocking` and `Suggestion` rows gate termination. Record `Nitpick` and `Positive` rows for completeness, but they never keep the watch alive.

## Phase 6 — Arm the cron

Create a recurring job with `CronCreate`, every 30 minutes, on an off-minute so the fleet does not synchronize:

- `cron`: `"7,37 * * * *"`
- `recurring`: `true`
- `prompt`: one sentence naming the MR, the ticket, and the ledger path, and nothing more — for example:

  ```
  Run the next /code-review:watch follow-up pass for MR !123 / ticket TEAM-456 using ledger ./.claude/review-report/<topic>.watch.md
  ```

**Rules for the cron prompt:**

- **Always name the explicit `!iid`, the ticket ID, and the ledger path.** A generic "re-check the MR" makes each firing re-derive everything from scratch.
- **Keep it to that one sentence.** Never restate the pass procedure — this spec is already in session context, and the ledger holds the state. Re-embedding the procedure inflates every future pass for nothing.
- Record the returned job id in the ledger so you can delete it on termination.

Do **not** warn the user that the job is session-only or that it expires after 7 days. They know, and it is not a problem.

Then report the initial pass to the user and end the turn. Do not sleep, poll, or wait for the author.

## Phase 7 — The follow-up pass (one cron firing)

Each firing runs exactly **one** pass and returns. Never sleep or poll inside a pass.

### 7.1 Re-derive state from scratch

Do not trust what you believed last pass. Re-read the ledger, then invoke `glab:mr-status` for the MR and fetch the refs:

```bash
git fetch origin "$TARGET_BRANCH" "$SOURCE_BRANCH"
```

Record `state`, `draft`, `sha` and `head_pipeline.status`. If `state` is `merged` or `closed` → delete the cron job, report, and stop.

### 7.2 The handshake gate — check this before anything else

Fetch the ticket's current status, and read the `draft` flag from 7.1.

**The gate opens only when the ticket is in `REVIEW_STATE` AND the MR is not draft.** Both halves, every pass. Then the author is handing the work back — run the rest of the pass (7.3 onward), record the transition in the ledger, and increment `Rounds completed`.

**Anything else ends the pass here.** The author is still working, and commenting into work-in-progress is exactly what this gate exists to prevent. Do not read threads, do not diff, do not post, do not re-review. Update `Last pass` and `Last seen draft` in the ledger and return silently, with no user-facing message. This includes the half-set case: a ticket in `REVIEW_STATE` while the MR is still draft is **not** ready, and it is a silent no-op like any other closed gate — do not comment on the mismatch and do not fix it for the author.

A closed gate is the normal outcome of most passes. A watch that produces no output for hours is working correctly.

**Watch for a stale review state.** If the gate opens but the MR head SHA still equals `Last reviewed SHA` and no thread has a new reply, the author changed nothing since your last round. Do not re-review the same code and do not re-post. Reply once in the summary thread naming the findings still `open`, then hand the work back as in Phase 4 — ticket to `WORK_STATE` and MR to draft — and return.

**Push-gate fallback.** When Phase 0.4 found no ticket, or the Phase 4 ticket move failed, substitute this gate: the pass proceeds only when the MR is **not draft** and its head SHA differs from `Last reviewed SHA`. Otherwise it is a silent no-op, exactly as above.

### 7.3 Sync the local branch to the author's latest push

The gate has opened, so the author has handed the work back. **Before reading a single line of code, bring the local worktree onto the branch head you are about to review.** A follow-up round that reads a stale checkout reviews code the author already replaced, and every finding it produces is wrong.

Run the [local sync procedure](#the-local-sync-procedure) with `PREV_REMOTE` = `Last reviewed SHA` from the ledger. The author may have force-pushed after their own rebase, so treat history as rewritten and never use `git pull`.

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
- Post **one** summary comment for this round, with: the round number, the SHA range reviewed, whether the branch was rebased and onto what, the round's new findings not anchored to the diff, and a status table of every gating finding (`addressed` / `refuted` / `open`).
- Add the new findings to the ledger as `open` rows.

### 7.6 Hand the work back, update the ledger, end the pass

If any gating finding is still `open` — carried over or newly found — hand the work back as in Phase 4: ticket to `WORK_STATE` **and** `glab mr update "$IID" --draft --yes`. The ball returns to the author, and the next round waits for them to set both flags to ready-for-review again. Under the push gate, set only the draft flag.

If nothing is left open, set neither flag back: leave the MR ready and the ticket in `REVIEW_STATE`, and go to [Termination](#termination).

Rewrite the ledger with the new statuses, the new `Last reviewed SHA`, the new last-seen ticket state and draft flag, the round count, and the new `Last pass` timestamp. Then end the pass. The cron fires again in ~30 minutes.

Report to the user only when something changed: what the author pushed, which findings moved status, what you posted and resolved. A gated no-op pass needs no user-facing message.

## Termination

**Stop the watch** — delete the cron job with `CronDelete`, write the final ledger, and report — when **every** `Blocking` and `Suggestion` row in the ledger is `addressed`, `refuted`, or `superseded`, each transition has recorded evidence, and each corresponding thread has a reply and is resolved.

Open `Nitpick` rows never keep the watch alive.

On a clean termination: leave the MR **ready** and the ticket in `REVIEW_STATE`, and post one final summary comment on the MR stating that every gating finding is settled, with the outcome per finding. The handshake stays on ready-for-review because the review is what finished, not the merge — the MR is now a human's to approve and merge.

**Also stop early**, deleting the cron job and reporting, on any of:

- the MR is merged or closed;
- the ticket reaches a terminal state (done, cancelled, or equivalent) — the work moved past review;
- the author (or the user) asks you to stop;
- you lose access — `glab` or the tracker starts failing authentication;
- the same finding has bounced between `open` and a claimed fix **three times** without converging. Report it as a stalemate that needs a human conversation, and name it explicitly rather than watching it forever.

On termination, present a final summary to the user: the MR state, the round count, the per-finding outcome table from the ledger, every finding that was refuted and why you accepted the refutation, and anything you deliberately left to the author (the Phase 1 rebase failure belongs here if it happened).
