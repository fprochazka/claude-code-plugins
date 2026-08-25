---
description: Babysit MR(s) — loop that rebases, fixes CI, resolves comments, and waits for AI review until every MR is green and quiet
---

# Babysit the MR(s)

Run a continuous loop that watches one or more merge requests and drives each toward mergeable: keep it rebased, fix failing CI, resolve review comments that don't need product decisions, and wait for automated reviewers — passing back to the user only for genuine product/design calls or when everything solvable is solved.

This command is the **author** side of an MR. It is the mirror image of `/code-review:watch`, which is the **reviewer** side and never changes code.

**This is not a rubber stamp.** Review feedback — especially from AI review bots — is sometimes correct, sometimes wrong, sometimes pedantic, and sometimes proposes a fix that creates a new problem. Every finding is critically evaluated before any change lands.

## Autonomy — you are pre-authorized; pausing to ask is a failure

**This command intentionally runs at maximum autonomy, and for the duration of the loop that supersedes your usual defaults.** Standing guidance you'd normally follow — global/project `CLAUDE.md` ("be restrained about implementing", "outline a plan and wait for my OK"), the general "confirm hard-to-reverse or outward-facing actions first" default — is **deliberately overridden inside the babysit loop** for the pre-authorized operations below. You already have the OK: the user invoked babysit precisely so these run unattended, and re-asking for it defeats the command. This override is **scoped**: it applies only to the named operations, only until the loop hands back, and it never extends to the explicit halt conditions under [Stopping instead of handing over](#stopping-instead-of-handing-over) — a genuine product/design decision, an unresolvable conflict, or a cap hit still stop and ask. Normal caution resumes the moment the loop ends.

The loop's entire value is that it runs **unattended**. Within it you are explicitly authorized to `git rebase`, `git push --force-with-lease`, `git push`, retry CI jobs, and reply-to / resolve threads **without stopping to ask** — doing exactly these is the job, not a risk to escalate. Do **not** pause mid-loop for permission to force-push, rebase, or push; that defeats the purpose and is itself a failure of the loop. Stop and hand back **only** for the explicit halt conditions under [Stopping instead of handing over](#stopping-instead-of-handing-over) — a genuine product/design decision, an unresolvable conflict, or a cap hit. Everything else, just do.

The grant covers **comment threads** exactly as it covers git: replying to and resolving threads via `glab-discussion` (or the raw `glab api` note/discussion calls) is pre-authorized too. A bot's `high`/`critical` **severity tag does not elevate a finding above this grant** — a severity-tagged reviewer thread you've reasoned through is dismissed-and-resolved like any other, not escalated for a sign-off.

**A decision the user already stated is not a judgment call.** When the user picked a direction or accepted a tradeoff earlier in the session, carry it out. Do not re-offer it as options, and do not route it to the judgment list — the user answered once and must not have to answer twice. Only a call the user has *not* made is a judgment call.

The grant also covers the **handoff controls**: toggling an MR between draft and ready (`glab mr update <iid> --draft --yes` and `glab mr update <iid> --ready --yes`), moving the ticket between `WORK_STATE` and `REVIEW_STATE`, posting the short factual MR or ticket comment that explains a move, and arming or deleting the handoff-wait cron job. These carry the same rule as everything else in this grant: do them, do not ask for them.

(If your harness's safety classifier blocks these git or discussion operations, that's an environment problem, not a signal to ask each time — the fix is to allowlist them once; see the plugin README. If a block lands mid-pass, don't stall the whole loop on it: note the exact blocked command **loudly** in the pass report, carry on with everything else and the other MRs, and let the allowlist fix land out of band — never sit and wait for a go-ahead on an operation the loop already authorized.)

## Prerequisites

- Each MR you're babysitting has its source branch checked out locally (in its own repo/worktree — a cross-repo change means several checkouts). The loop rebases and pushes each.
- `glab` and `jq` available.

## Tooling — prefer the helpers, fall back to raw `glab`

Two purpose-built CLIs make this loop cleaner; **check for each once at setup** (`command -v glab-pipeline`, `command -v glab-discussion`) and prefer it when present, otherwise fall back to raw `glab api` / `glab ci`:

- **`glab-pipeline`** (CI triage) — if missing, use `glab ci get --with-job-details -F json` to list jobs and `glab ci trace <job-name> > /tmp/babysit-job-<name>.log 2>&1` (always redirect — traces are huge) for each failed job's log.
- **`glab-discussion`** (comment threads) — if missing, use `glab api "projects/:id/merge_requests/<iid>/discussions" --paginate` to read, `glab api -X POST ".../discussions/<id>/notes" -f body=@<file>` to reply, and `glab api -X PUT ".../discussions/<id>" -F resolved=true` to resolve.

The steps below name the preferred tool first, then the fallback. Install the helpers for the better experience: `uv tool install glab-pipeline glab-discussion`.

## Setup (once, before the loop)

### 1. Establish the MR set — explicit or session-derived only

A change often spans **more than one MR** (e.g. a service repo + a data/ETL pipelines repo). The loop babysits a **set** of MRs, and every pass covers **all of them** — a common failure is silently babysitting only the MR in the current directory while its sibling drifts behind master. The set comes from exactly two sources:

- **MRs the user explicitly named** — URLs or `!iid`s in the invocation or the loop prompt.
- **MRs this session created or worked on** — ones you opened via `glab mr create`, or that a session recap/handover in context names as this work's MRs. **If a `session-distill` / handover recap is present, actively scan it for `!iid`s and MR URLs before finalising the set** — a prose recap that names a sibling MR (e.g. an airflow/ETL repo alongside the service repo) is the *primary* source of session-derived MRs, and the recurring miss is not synthesising it from the recap and babysitting only the current worktree's MR. Don't rely on memory; pull the iids out of the recap explicitly.

**Do not go discovering "related" MRs** by scanning other repos, searching the group, or guessing from branch names — that risks pulling in unrelated work, which is explicitly unwanted. If you have concrete reason to believe a sibling MR exists but it wasn't named and you didn't work on it (e.g. you edited a second repo this session but weren't told its MR), **ask the user** to confirm the set rather than auto-adding it. If nothing was named and the session created nothing, default to the current branch's single MR.

State the resolved set back to the user as the **very first line of pass 1, before running any tool** ("babysitting MR !123 and !456") — not buried in the end-of-pass report after the loop has already been armed for the wrong subset. That way a missing sibling surfaces before any work happens.

### 2. Record each MR and run safety checks

For **each** MR in the set, record its **repo/worktree path**, then invoke the `glab:mr-status` skill to read that MR's state (run from that worktree, or with the repo named explicitly). Carry these fields: `iid`, `state`, `draft`, `web_url`, `source_branch`, `target_branch`, `sha`, `head_pipeline` (`status`/`id`/`web_url`), `blocking_discussions_resolved`.

Record `draft` on **every** read of an MR, here and at each pass gate. It is one half of the handshake in setup step 3, and a pass that forgets it hands the ball over with the wrong signal.

> Don't assume the output format of any `glab` call — a token-reducing proxy in front of `glab` (e.g. [`rtk`](https://github.com/rtk-ai/rtk)) can reshape or compress it, so `--output=json` may not come back as JSON. Rather than blindly probing format variations, run a command **once, unfiltered**, read the actual output, and derive from that how to pull the fields you need on every following call. (`glab api "projects/:id/merge_requests/<iid>"` returns raw JSON if you want a clean source.)

Then, per MR, **refuse and drop it from the set (report why) if any safety check fails:**
- Its source branch is checked out in its worktree (`git branch --show-current` equals `source_branch`). Never auto-checkout a different branch.
- The branch is **not** `master`/`main` (guards against pushing to the default branch).
- That worktree is clean (`git status --porcelain` empty). If dirty, surface and skip that MR — the loop rebases and force-pushes, unsafe over uncommitted work.

Drop any MR whose `state` is `merged`/`closed`. If the set is empty after this, report and stop.

### 3. Resolve the ticket and its workflow states

Invoke the `sdlc:team-workflow-identify` skill and carry its output block for the whole run. It names the tracker, the ticket ID pattern, and the state names this command moves the ticket between. Then load the installed skill that covers the resolved tracker — that skill holds the command syntax, and this command names no tracker CLI of its own.

Take the ticket from the MR title, the branch name, or the MR description, using the ticket pattern from the block. Several MRs in the set usually share one ticket.

**The handshake invariant.** Ready-for-review means the MR is **not draft** AND the ticket is in `REVIEW_STATE`. Back-to-work means the MR is **draft** AND the ticket is in `WORK_STATE`. The two flags always move together. Whoever hands the ball over sets both.

`/code-review:watch` is the other half of that handshake. It reads both flags before it reviews, so a half-set handshake either starts a review of work in progress or leaves a finished MR unreviewed.

**Reclaim an MR that is not draft while work is pending.** At setup, and again at each pass gate, an MR that is **not draft** while this pass has work to do — behind its target branch, red pipeline, or open in-scope threads — is claimed back before that work starts:

```bash
glab mr update <iid> --draft --yes
```

Move the ticket to `WORK_STATE` in the same step, and post one MR comment stating the reason in one line (for example "taken back to draft: pipeline is red on `<sha>`"). State the fact and nothing else — promise no fix, no timeline, and no follow-up.

If the block says `tracker: none`, or no ticket is identifiable, the handshake **degrades to the draft flag alone**. Everything below still runs, and every ticket move is skipped rather than faked.

### 4. Write the babysit ledger

Write `./.claude/review-report/<topic>.babysit.md`, and rewrite it at the end of every pass. It holds only what must survive a context compaction or a fresh cron firing — the working state stays in session context.

```markdown
# Babysit ledger: <topic> (MR !<iid>, !<iid>)

- MRs: <repo!iid — worktree path — draft yes|no> (one line each)
- Ticket: <TICKET-ID> (<url>) — handshake: ticket+draft | draft-only
- Work state: <WORK_STATE> · Review state: <REVIEW_STATE>
- Mode: working (`/loop` 2m) | handoff-wait (cron <id>)
- Last pass: <UTC timestamp>
```

## Driving the cadence

**Do not sleep, poll, or wait inside a pass, and do not use the Monitor tool.** Run **exactly one pass** (covering every MR in the set), then return. Re-running every ~2 minutes is delegated to the native `/loop`.

The command runs at **two cadences**. This section describes the **working cadence** — a `/loop` every ~2 minutes while there is anything to rebase, fix, or answer. Once every MR is handed over, the loop switches to the slower **handoff-wait cadence** under [Handoff](#handoff).

These instructions are already in context after this first read, so **don't re-invoke the whole command** each cycle — that re-injects the entire spec for nothing. Instead kick off the loop with a lightweight reminder prompt naming the MRs:

```
/loop 2m re-check MR !123 and !456 and run the next babysit pass
```

**Rules for the reminder prompt:**
- **Arm the loop by calling it, not by printing it.** The pass ends with a real invocation — the loop skill for the working cadence, `CronCreate` for the handoff-wait cadence — and the pass report names the job id it returned. Writing the `/loop 2m …` line into the report as text arms nothing: the loop never fires, and the user ends up hand-driving every rebase and comment read for the rest of the session. If you cannot name a job id, the loop is not running.
- **A cron prompt is plain text and never contains a slash command.** A `/loop …` or `/sdlc:mr-babysit …` inside the prompt re-enters the command on every firing and stacks a new cron each time.
- **Always name the explicit `!iid`s** — `re-check MR !123 and !456`, never a generic "re-check the MR". A prompt without iids makes each iteration re-discover the set from the current branch and silently drops any sibling MR.
- **Keep it to that one sentence.** Never restate the pass procedure in the prompt — the spec and per-MR state already persist in session context; re-embedding the gate/CI/comment/handoff steps inflates every future pass's token cost for nothing.
- **Don't tune the interval to CI duration.** Hold the ~2 min cadence even when the pipeline takes 20+ minutes — a slow pipeline just yields cheap no-op passes and keeps you responsive to new reviewer comments. Don't stretch the interval to "save" passes, and don't swap the recurring `/loop` for a one-shot `ScheduleWakeup` (or a `CronCreate` with a hardcoded SHA in its prompt): a one-shot needs manual rescheduling each pass and silently dies if a pass errors before it reschedules, and a hardcoded SHA goes stale the moment you push. This rule governs the working cadence. The handoff-wait cadence uses a **recurring** cron on purpose, and its prompt carries no SHA.
- **If the set changes mid-session** (the user names an additional MR), update the running loop prompt to name **all** MRs — don't rebase/push the newcomer once and move on; it needs the same periodic gate cadence, or its pipeline goes unwatched for the rest of the session.
- **Never end a pass by asking "should I continue?"** If anything is still pending — pipeline running, threads open, a push just landed — the correct move is to *stay in the loop*: emit/keep the `/loop 2m …` and let the next pass re-check. Presenting options or waiting for a go-ahead to run the next pass is the same autonomy failure as pausing mid-pass.

Session context persists across iterations, so the full pass procedure plus per-MR state (CI/flaky attempt caps, oscillation tracking, the judgment list) carries over. The ledger from setup step 4 holds only the handful of facts that must outlive a compaction or a fresh cron firing. Because the gate (step 1) re-checks pipeline status and new comments on every pass, "wait for the pipeline, then give an AI reviewer a couple of minutes" happens *naturally across passes*: a pass that finds the pipeline still running just does nothing actionable and returns, and a later pass picks it up once it's green. When the handoff condition is met, stop the `/loop` and switch to the handoff-wait cadence.

## The loop — one pass

Each pass iterates **every MR in the set**; for each MR, `cd` to its worktree and run steps 1–5 below, tracking attempt caps and the judgment list **per MR**. Then do the single end-of-pass report (step 6). A pass that pushes anything lets the next pass (≈2 min later) watch the resulting pipeline.

### 1. Gate

Invoke `glab:mr-status` for this MR. If `state` is `merged`/`closed` → drop it from the set (report), and if the set is now empty, **stop the loop**. Otherwise read `draft`, `head_pipeline.status`, `target_branch`, `sha`, `blocking_discussions_resolved` for the steps below.

If this MR is **not draft** and steps 2–4 have work to do, reclaim it before doing that work — see setup step 3.

**Re-verify your own resolves from the previous pass.** Resolve state is not reliably sticky: a thread you resolved can read unresolved again a few passes later, and a diff note can return 404 right after an amend + force-push. Both are a re-do, not a failure — resolve the thread again, or re-post the note against the current head, and carry on. Do not treat either as a broken tool or a reason to surface anything.

### 2. Keep it rebased

```bash
git fetch origin "$TARGET_BRANCH"          # fetch ONLY the target branch — see note below
git rev-list --count HEAD..origin/"$TARGET_BRANCH"
```

If the count is `> 0`, the branch is behind:

```bash
git rebase origin/"$TARGET_BRANCH"
```

- **On conflict → resolve it yourself.** Read both sides, understand what each change intended, and reapply the MR's intended change on top of the target branch's new state — the target branch is the base you're building on, and the MR's change is what must survive, adapted to that base (not a mechanical union of both hunks). Verify the result builds/tests where feasible before continuing. Rebasing is safe because git's reflog holds every prior state: as long as you use git properly at each step (no `--no-verify`, no destructive resets over unstaged work), you can always recover — `git reflog` then `git reset --hard <pre-rebase-sha>` (or `git rebase --abort` while mid-rebase) rewinds to before the rebase. So attempt the resolution rather than bailing.
  - **Only surface + stop** when a conflict encodes a genuine **product or design decision** — two intended behaviours that can't both be right, and picking one is a call the user must make. Mechanical conflicts (imports, formatting, adjacent edits, a rename vs. an edit) are yours to resolve.
- On clean rebase → the branch is pushed together with any other fixes this pass (step 5). If the rebase is the *only* change, push it: `git push --force-with-lease`.

> Fetch **only** `$TARGET_BRANCH`, never a bare `git fetch origin` — a bare fetch also updates `origin/<source_branch>`, which defeats the no-arg `--force-with-lease` (its expected value becomes whatever was just fetched, silently overwriting a teammate's push). If you must fetch the source branch, capture the pre-fetch SHA and push with `--force-with-lease=<branch>:<pre-fetch-sha>`.
>
> This holds in **every** step, not just the rebase — don't `git fetch origin` bare at setup or during push-verification either. To read the remote after a push, use `git rev-parse origin/<source_branch>` (your own push already advanced the tracking ref) or `git ls-remote origin <source_branch>`, never a bare fetch.

### 3. Fix failing CI

If `head_pipeline.status` is `failed`, triage it (a red build blocks merge, so handle it this pass):

Run `glab-pipeline inspect` and read its printed summary and `summary.json` first (they point at the failed jobs and reasons), then the referenced `job-logs/`, `test-report.json`, or `merged.yml`.

Diagnose each failure **critically — the log is a symptom, not a verdict**:

- **Fixable** — compile error, lint/format/checkstyle, missing import, a test failing clearly because of *this MR's* diff, an assertion/snapshot that legitimately must change → fix it. **Verify locally when feasible** (run the failing test or the narrowest slice in the checked-out repo and confirm green) before pushing, rather than burning a full CI cycle on a blind push.
- **Flaky / infra** — runner lost, network/timeout, OOM, a test unrelated to the diff → **not** a code fix. **Retry the job** (`glab ci retry <job-name>`) to try to get past it, but **complain loudly**: in the pass report, name the job, why you read it as flaky, and that you retried it — so the user can later decide whether it deserves a separate task (quarantine the test, fix the infra). Never paper over a flake with a code change. Cap retries at **2 per job signature** in this session; if it's still flaky after that, keep it in the loud report and stop retrying it. **A second failure of the *same* job is a signal to scrutinize, not to reflexively retry** — a "flake" that reproduces may be your own regression; bisect it before assuming infra.
- **Judgment-heavy** — a behavioural test whose *correct* expectation is unclear, a failure rooted in code outside the MR's scope, an ambiguous root cause, or anything you're less than ~90% sure how to fix → surface it and add it to the judgment list (step 6).

**Attempt cap.** Track, in this session, a stable **failure signature** per fixable failure (e.g. `test:<Class>#<method>`, `build:compile`, `lint:<rule>`) and how many times you've pushed a fix for it. After **2 attempts** on the same signature still failing → stop fixing it, surface it ("attempted twice, still red — over to you"), and stop the loop. This is what prevents a fix that never converges from churning CI forever.

Fixes join step 5's single rebase + push.

### 4. Address review comments

Read the discussion threads with `glab-discussion read --dump` — one file per thread with resolved status, author, bot markers, and diff-note positions.

A thread is **in scope** iff it is unresolved **and** the most recent non-system note's body does **not** end with the marker `<!-- babysit:auto-reply -->` (last-line equality, never a substring — AI review prose often quotes the marker in backticks). Skip threads where every note is a system note (label changes, commit-status updates).

**Your own authorship is irrelevant to scope.** Threads you posted earlier this session under a different hat — e.g. via `/code-review:post` — look like fresh external threads and *are* in scope: run them through the same four outcomes below as ordinary reviewer feedback. Do **not** halt the loop because you recognise a comment as your own; "these are the findings I just posted" is not a reason to stop and ask, and auto-dismissing a wrong one of your own findings is not circular — evaluating each on its merits is exactly the job.

For each in-scope thread, reach **one of four outcomes** — critically evaluated, never a reflexive apply:

- **Apply** — the finding is correct, the fix is sound, and it doesn't ripple into adjacent code that wasn't shown. Before applying: re-read the cited file/line yourself (AI quotes routinely misread context), check the fix doesn't contradict an earlier fix this run (oscillation), and confirm it's at the right layer (root cause, not symptom). → fix it (batched into step 5), reply linking the fix, resolve.
- **Dismiss** — the finding is wrong, marginal, pedantic, or already covered. → reply with the *specific reasoned disagreement* ("line X does not say what the finding claims", or "applying this would break Y"), resolve.
- **Judgment** — the finding is real but the fix needs a product or design decision (public API change, migration, behavioural tradeoff, off-by-one where the boundary is semantic, architecture pushback, "why did you…" questions). → collect it for step 6. **Do not stop the loop for it, and never reach for `AskUserQuestion` or any other blocking prompt to raise it** — defer it to the non-blocking step-6 report and keep solving everything else, ending the pass normally even when a judgment call is the *only* thing outstanding (the user replies before the next pass fires; a blocked pass just wastes the loop tick). Post no marker, so it re-enters scope if the user later addresses it. A finding you've already deferred that the bot re-raises → dismiss with a reference to the standing deferral and resolve (don't re-surface the same call every pass).
- **Skip this pass** — looks fine but you're not confident enough. → do nothing (no reply, no marker); it re-enters scope next pass.

**Comment rules:**
- **Execute dispositions in the pass — don't pre-clear them.** Once you've decided Apply / Dismiss / Resolve for a thread, do it: reply and resolve in the same pass. Do **not** post a "here's my proposed disposition for each thread, awaiting your go" summary and wait — those actions are pre-authorized. The only outcome that waits is a **Judgment** call, which goes to the step-6 report unexecuted.
- Reply body must end with a blank line then `<!-- babysit:auto-reply -->` so handled threads aren't re-processed. Write multi-line bodies to a temp file (`/tmp/babysit-reply-<id>.md`) to avoid shell-quoting breakage, then `glab-discussion write --reply-to <id> --body - < /tmp/babysit-reply-<id>.md` and `glab-discussion resolve <id>`.
- **A watch thread gets a reply and never a resolve on your own initiative.** A thread whose most recent reviewer note ends with the marker `<!-- code-review:watch -->` (last-line equality) belongs to `/code-review:watch`. Apply the fix, or reply with the reasoned disagreement, then **leave it unresolved**. The reviewer verifies the fix against the code at the MR head and resolves it. Resolving it yourself removes the reviewer's only signal that the finding still needs checking, and the reviewer un-resolves it again. The one exception is the user telling you to resolve a specific watch thread — that is the human's decision to make, and then you carry it out. Every other thread keeps the ordinary resolve rules.
- **A general note with no `Resolved` field cannot be resolved.** GitLab answers the resolve call with HTTP 403, which is the API refusing an unresolvable note, not a permission problem — the typical case is a review bot's "rebase detected, skipping review" informational note. Attempt it once, note it in the pass report, and never retry it. An unresolvable note never blocks the handoff condition.
- **Delegating a reply or a resolve to a subagent means handing over the full discussion id** from the `glab-discussion` dump, never a shortened prefix. The CLI rejects a prefix, and the subagent then has to dig the full id out of the dump files itself.
- **Resolve only threads you fully handled** — one you applied a sound fix for, or dismissed with a reasoned reply. This includes a **human's** thread when it is *truly addressed* (the fix does exactly what they asked, or your reply squarely answers them). But hold back on a human thread when it's borderline: if the person may want to eyeball the fix, if your reply is a judgment call they might disagree with, or if you're unsure what they meant — leave it unresolved (or route it to Judgment) so they get the last word. Bot nits you fully handled always resolve.

### 5. Commit, push & verify the push landed (once per pass per MR)

If this pass produced any changes (a rebase, CI fixes, or applied comment fixes), batch them into a single push:

- Re-read the diff yourself before pushing.
- Commit with a clear conventional message. **Never** `--no-verify` and never bypass hooks — if a pre-commit hook fails, fix the underlying issue; skipping hooks to make an error go away is not allowed (this includes fixups and reverts). If a compound command like `git add -A && git commit …` is blocked or errors, run the steps separately and check each — don't assume it worked.
- Before `git commit --fixup <sha>`, **confirm the target commit is the one that introduced the lines you are fixing** — `git log -S '<a distinctive line>' -- <file>`, or `git log --oneline -- <file>` when the file is new. A later commit often moves, extracts, or renames those lines, so the obvious-looking parent is the wrong one and the fixup conflicts on replay.
- If you need to **reword existing commits** (e.g. add a ticket prefix to the branch's messages), use a targeted `git rebase` with `--exec 'git commit --amend --no-edit …'` or explicit reword steps — **not** `git filter-branch`, which is deprecated and silently mangles edge cases (empty commits, merges, grafted history).
- `git push --force-with-lease` if the parent chain was rewritten (rebase), otherwise `git push`. **Never** bare `--force`.
- **Verify the push actually landed — never narrate a push as done without checking the remote.** After pushing, confirm `git rev-parse origin/<source_branch>` equals your local `HEAD`, and that the commit you intended is really there (`git log origin/<source_branch> -1` shows your subject; the files you changed are in `git show --stat`). **The push command's own output showing an `old..new` SHA delta does not count as this check** — run the `git rev-parse origin/<source_branch>` compare explicitly, every push; treating the push output as confirmation is the exact habit that lets a partial or misdirected push read as success. This is the guard against the failure mode of reporting "fixed and pushed" when a blocked/failed command actually staged or pushed nothing. If the remote didn't advance, the push did **not** happen — diagnose and redo it before reporting.
- Then post the per-thread replies and resolves from step 4 (reply first, then resolve; if a reply fails after one retry, do **not** resolve — surface it).

### 6. Report (non-blocking) & end the pass

**Rewrite the ledger (setup step 4) before you write the report.** A compaction landing between the two loses the hand-back, and the ledger is the only thing that survives it — so it must already hold the current state when the report is written.

Do one report for the whole pass, **without blocking** for a reply. For each MR, give a one-line **handoff scorecard** so convergence is visible, plus what happened:

```
MR !123  green ✓ · quiet ✓ (3m) · threads ✓     → ready to hand over
MR !456  green ✗ (running) · quiet — · threads ✓ → waiting on pipeline
MR !789  green ✓ · quiet ✓ · threads ✗           → waiting on local verification (subagent :app:test, 12m)
```

**Waiting on your own local verification is a third state, distinct from waiting on the pipeline.** A long local test run produces a stretch of identical no-op passes, and a scorecard that reads `waiting on pipeline` through all of them hides what the real blocker is. Name the command and how long it has been running.

Include: what was rebased/fixed/applied (with commit SHA and the verified-landed remote SHA), what was dismissed, any flaky jobs you retried (loudly), and the running list of **judgment calls**. Then **end the pass** — do not sleep, poll, or wait; the native `/loop` re-runs the next pass in ~2 minutes (see "Driving the cadence"). A pass that pushed anything, or that found a pipeline still running/pending, has nothing more to do this cycle — the next pass re-checks at the gate once ~2 min have elapsed (enough for a pipeline to progress and an AI reviewer to post). If the handoff condition below is met for **all** MRs, hand over instead of returning to the working cadence.

## Handoff

### The handoff condition

Hand the MR set over when **every MR in the set** satisfies **all** of these:

1. The pipeline is **green** (`head_pipeline.status == "success"`). `canceled`, `manual` and `skipped` are not green.
2. It has been **≥2 minutes quiet** since the pipeline finished — no new comments have appeared (gives an AI reviewer time to weigh in on the final commit).
3. Every actionable comment has a reply, and every thread you handled is resolved. Watch threads carry a reply and stay unresolved, which is the settled state for them.
4. The only remaining open threads, if any, are **Judgment** calls or **Skips**, watch threads you answered, or human threads left for the human to close.
5. No **judgment call** is outstanding. An outstanding judgment call means the change is not finished, so the MR stays draft and the ticket stays in `WORK_STATE`, and you hand back to the user instead.
6. The branch is **not behind its target branch** — or the divergence provably does not touch this MR. Master often moves faster than a long pipeline finishes, so a rebase-then-wait cycle can never converge. Compare the target's new commits against the MR's own files (`git diff --stat origin/<target>...HEAD` for the MR's file set, `git diff --stat HEAD..origin/<target>` for the new commits' file set) and hand over behind **only** when the two sets do not intersect. Say it in the handover line: "4 commits behind master, docs-only, no overlap with this MR". Any overlap means rebase first and let the next pass watch the resulting pipeline.

### Hand the ball over

Set both halves of the handshake. Mark every MR in the set ready:

```bash
glab mr update <iid> --ready --yes
```

Move the ticket to `REVIEW_STATE` **once**, when every MR on that ticket qualifies. One MR going green while its sibling is still red is not a handover — the reviewer would read a half-finished change. Post one short MR comment per MR saying it is ready and what the last pass changed. State facts only, and promise nothing.

Then update the ledger and **do not stop**. The reviewer now has the ball, and the reviewer hands it back through the same two flags.

### The handoff-wait cadence

Delete the 2-minute `/loop` and arm a recurring `CronCreate` every 30 minutes on an off-minute, so the fleet does not synchronize:

- `cron`: `"13,43 * * * *"`
- `recurring`: `true`
- `prompt`: one sentence naming the MRs, the ticket, and that this is a wait pass — for example:

  ```
  Run the next /sdlc:mr-babysit handoff-wait pass for MR !123 and !456 / ticket TEAM-789 using ledger ./.claude/review-report/<topic>.babysit.md
  ```

Record the returned job id in the ledger. Never restate the pass procedure in the prompt, and never put a SHA in it.

**Each wait pass re-derives state and does one of four things:**

- **The ticket is back in `WORK_STATE`, or any MR is draft again** → the reviewer handed it back. Delete the cron job, re-arm the 2-minute `/loop` with the same MR set, and run a normal working pass. New reviewer threads are ordinary in-scope threads under step 4.
- **All MRs are still ready and the ticket is still in `REVIEW_STATE`** → nothing to do. Update `Last pass` in the ledger and return with no user-facing message. A wait mode that is silent for hours is working correctly.
- **Every MR is merged or closed, or the ticket reached a terminal state** → delete the cron job, write the final ledger, report, and stop for good.
- **A new comment thread appeared while the flags did not move** → an AI reviewer or a person commented without handing the work back. Treat it as a normal working pass for that thread only: re-arm the working cadence, answer it, and hand over again when the set is quiet.

When `tracker: none` degraded the handshake to the draft flag alone, the wait pass reads only the draft flag: any MR back in draft re-arms the working cadence.

The user can opt out of the wait with an explicit "stop after handoff". Then the handover is the last thing this command does — report and end, arming no cron job.

### Stopping instead of handing over

**Stop and hand back to the user** (report, arm no cron job) on any of: all MRs merged/closed; a rebase conflict that encodes a genuine product/design decision (mechanical conflicts you resolve yourself); a CI failure surfaced as judgment-heavy, or a fixable failure (or a flaky job) that hit its 2-attempt cap and is still red; a reply/resolve that kept failing after a retry; oscillation (this pass's fix contradicting last pass's); or an outstanding judgment call with nothing else left to solve. A halt on one MR doesn't have to halt the others — keep babysitting the rest and report the one that needs you.

Whenever you stop this way, the MRs concerned stay **draft** and the ticket stays in `WORK_STATE`. The work is not ready, so the handshake must not say it is.

Present a final summary: the per-MR scorecard, what you did, each MR's state, whether you handed over or stopped, and — as a clear list — every **judgment call** you deferred (thread location + quoted comment + your suggested reply or change), and ask the user how to proceed.

$ARGUMENTS
