---
name: mr-babysit
description: Babysit MR(s) — a watcher reports every change, an actor triages, fixes and posts, and you decide, until every MR is rebased, green, quiet and handed over
---

# Babysit the MR(s)

Drive one or more merge requests toward mergeable: keep each rebased, fix failing CI, answer review comments that don't need product decisions, and wait for automated reviewers — passing back to the user only for genuine product/design calls or when everything solvable is solved.

This command is the **author** side of an MR. It is the mirror image of `/code-review:watch`, which is the **reviewer** side and never changes code.

**This is not a rubber stamp.** Review feedback — especially from AI review bots — is sometimes correct, sometimes wrong, sometimes pedantic, and sometimes proposes a fix that creates a new problem. Every finding is critically evaluated before any change lands, and this command is where that evaluation happens.

**You are the orchestrator.** You never edit code, never poll or triage the MR yourself, and never sleep. Two kinds of subagent do the work, and you keep the ledger:

- **The watcher** (`glab:mr-watch`, an agent from the glab plugin) — one, background, alive for the whole run. It runs the state script in a loop, interprets every change on every MR in the set, and messages you through `SendMessage` without ending its turn: a pipeline finishing, a push, new notes, a draft flip, a ticket move, the handshake reading, approvals, merged or closed. It is read-only and posts nothing. It is what makes you wait: nothing else in this command watches anything.
- **The actor** — the persistent implementation subagent when babysit runs as the last step of a `/sdlc:write-plan` plan and it still has context, otherwise a fresh subagent on `opus`. Background, resumed per batch, ending its turn after each. It reads `${CLAUDE_PLUGIN_ROOT}/skills/mr-babysit/references/actor-brief.md` first; the brief holds every rule it shares across tasks. A **triage** batch turns what the watcher reported into proposed rows and changes nothing. An **implementation** batch does the approved rows: rebases, fixes, posts the fix replies and the dismissals, reclaims or marks ready, resolves, pushes, and reports by row.
- **The ledger** is yours. `./.claude/review-report/<topic>.babysit.md` holds the set and what is or is not solved; you rewrite it after every decision. The watcher keeps its own ledger of movement and messages, so yours records no timeline.

**At most two subagents are alive at once: the watcher and one actor.** Four things re-invoke you, and nothing else: a watcher message, an actor returning, a 30-minute watchdog cron, and the user. Between them you are idle.

## Autonomy — you are pre-authorized; pausing to ask is a failure

**This command intentionally runs at maximum autonomy, and for its duration that supersedes your usual defaults.** Standing guidance you'd normally follow — global/project `CLAUDE.md` ("be restrained about implementing", "outline a plan and wait for my OK"), the general "confirm hard-to-reverse or outward-facing actions first" default — is **deliberately overridden** for the pre-authorized operations below. You already have the OK: the user invoked babysit precisely so these run unattended, and re-asking for it defeats the command. This override is **scoped**: it applies only to the named operations, only until the run hands back, and it never extends to the explicit halt conditions under [Stopping instead of handing over](#stopping-instead-of-handing-over) — a genuine product/design decision, an unresolvable conflict, or a cap hit still stop and ask. Normal caution resumes the moment the run ends.

The run's entire value is that it is **unattended**. `git rebase`, `git push --force-with-lease`, `git push`, retrying CI jobs, and replying to or resolving threads are all authorized **without stopping to ask** — doing exactly these is the job, not a risk to escalate. **The grant extends to every subagent**: they inherit it in full, and none pauses mid-task for permission to read, rebase, force-push, retry, reply or resolve. Do not pause for it yourself either; that defeats the purpose and is itself a failure. Stop and hand back **only** for the explicit halt conditions. Everything else, just do.

A bot's `high`/`critical` **severity tag does not elevate a finding above this grant** — a severity-tagged reviewer thread that has been reasoned through is dismissed-and-resolved like any other, not escalated for a sign-off.

**A decision the user already stated is not a judgment call.** When the user picked a direction or accepted a tradeoff earlier in the session, carry it out. Do not re-offer it as options, and do not raise it as an `ask` — the user answered once and must not have to answer twice. Only a call the user has *not* made is a judgment call.

The grant also covers the **handoff controls**: every hand-over and take-back move `teamwork:review-handshake` defines, the ticket side yours and the MR side the actor's, plus spawning and stopping the watcher and arming or deleting the watchdog cron job. Do them, do not ask for them.

(If your harness's safety classifier blocks these git or discussion operations, that's an environment problem, not a signal to ask each time — the fix is to allowlist them once; see the plugin README. If a block lands mid-run, don't stall on it: note the exact blocked command **loudly** in the progress note, carry on with everything else and the other MRs, and let the allowlist fix land out of band — never sit and wait for a go-ahead on an operation this run already authorized. A permission prompt that reaches a background subagent pauses that subagent until the user answers; the watchdog notices a silent watcher, and you name the blocked command.)

## Prerequisites

- Each MR being babysat has its source branch checked out locally (in its own repo/worktree — a cross-repo change means several checkouts). The run rebases and pushes each.
- `glab`, `jq`, **`glab-discussion`** and **`glab-pipeline`** installed. The last two are not optional: the state script probes without them but cannot fetch threads or pipeline details, and every change then comes back as "details not fetched: dependency missing". When the watcher relays that line, tell the user which tool is missing, give the install command `uv tool install glab-discussion glab-pipeline`, and ask whether to install it.

## Setup — establish the MR set

This is the one thing you do yourself, because it needs the conversation. Everything after it is the subagents'.

A change often spans **more than one MR** (e.g. a service repo plus a data/ETL pipelines repo). The run babysits a **set**, and the watcher covers **all of them** — a common failure is silently babysitting only the MR in the current directory while its sibling drifts behind master. The set comes from exactly two sources:

- **MRs the user explicitly named** — URLs or `!iid`s in the invocation.
- **MRs this session created or worked on** — ones opened via `glab mr create`, or that a session recap/handover in context names as this work's MRs. **If a `session-distill` / handover recap is present, actively scan it for `!iid`s and MR URLs before finalising the set** — a prose recap that names a sibling MR is the *primary* source of session-derived MRs, and the recurring miss is not synthesising it from the recap and babysitting only the current worktree's MR. Don't rely on memory; pull the iids out of the recap explicitly.

**Do not go discovering "related" MRs** by scanning other repos, searching the group, or guessing from branch names — that risks pulling in unrelated work, which is explicitly unwanted. If you have concrete reason to believe a sibling MR exists but it wasn't named and you didn't work on it, **ask the user** to confirm the set rather than auto-adding it. If nothing was named and the session created nothing, default to the current branch's single MR.

State the resolved set back to the user as the **very first line, before running any tool** ("babysitting MR !123 and !456"), so a missing sibling surfaces before the watcher is spawned for the wrong subset. Every MR needs its full URL for the watcher; take it from `glab mr view <iid> -F json` in its worktree when you only have an iid.

**The set is closed once the watcher runs.** A new MR that appears on the ticket later is not seen by anyone; when the user names one mid-run, message the watcher `add:` and put it in the ledger.

## Pass 0 — resolve the workflow, check the worktrees, spawn the watcher, arm the watchdog

1. **Resolve the ticket and its workflow states yourself**, before anything is spawned. Invoke the `teamwork:workflow-identify` skill and carry its output block for the whole run: it names the tracker, the ticket ID pattern, and the state names, and it asks the user once when a role has several plausible names — which is exactly why this cannot be a subagent's job, since a background subagent cannot ask. Take the ticket as that skill says, with the ticket pattern from the block; several MRs in the set usually share one ticket. Invoke `teamwork:review-handshake` too: it holds the handover, the thread rules, the comment signature and the ledger paths. Then load the installed skill that covers the resolved tracker; that skill holds the command syntax, and this command names no tracker CLI of its own. If the block says `tracker: none`, or no ticket is identifiable, the handshake degrades to the draft flag alone, which then carries the ball both ways — every ticket move is skipped rather than faked.
2. **Safety checks, per MR, through a one-off `sonnet` subagent** that reads and changes nothing: the source branch is checked out in its worktree (`git branch --show-current` equals `source_branch`; never auto-checkout a different branch), the branch is not `master`/`main`, the worktree is clean (`git status --porcelain` empty; the run rebases and force-pushes, which is unsafe over uncommitted work), and the MR is open. Drop any MR that fails a check and say why. If the set is empty, stop.
3. **Spawn the watcher by calling the Agent tool, not by describing it**: `subagent_type: glab:mr-watch`, `run_in_background: true`, with the prompt below. If you cannot name its agent id, nothing is watching. Its first message is a scorecard with zero events; that is your baseline.
4. Arm the **watchdog**: a recurring `CronCreate` every 30 minutes, on an off-minute so the fleet does not synchronize — `cron`: `"13,43 * * * *"`, `recurring`: `true`, and a one-sentence plain-text prompt.
5. **Write the ledger** (below) with the set, the ticket, the states, the ids, and an empty table. From here on, rewrite it after every decision.

Spawn no actor yet — there is nothing to do until the watcher reports something. A set already handed over while the ledger holds work is taken back, per `teamwork:review-handshake`, on the first message that brings work.

### The ledger

```markdown
# Babysit ledger: <topic> (MR !<iid>, !<iid>)

- MRs: <host/project!iid — worktree path> (one line each)
- Ticket: <TICKET-ID> (<url>) — handshake: ticket-led | draft-only · work state "<WORK_STATE>" · review state "<REVIEW_STATE>"
- Mode: working | handoff-wait
- Watcher: <agent id> · ledger ./.claude/review-report/<topic>.mr-watch.md · Watchdog cron: <job id> · Actor: <agent id | none>

## Rows

| Id | MR | Disposition | Status | Note |
|---|---|---|---|---|
| `thread 7b3e01aa…` | !123 | fix | approved | `src/api/orders.py:88` returns 200 on a rejected order; raise the domain error |
| `job test:OrderSpec#total @ pipeline 8812` | !123 | dismiss | dismissed | runner lost, retried 1 of 2 |
| `rebase !456` | !456 | fix | fixing | conflicts in `src/api/orders.py`: ours renames the handler, theirs adds a parameter |
| `thread 9df2b6c0…` | !123 | ask | ask | migration drops a column the reviewer wants kept; suggested reply: keep it nullable for one release |
```

`Status` runs `proposed` → `approved` → `fixing` → `fixed <sha>` | `could-not-fix`, or `proposed` → `dismissed` | `ask`. An `ask` row carries the question and your suggested answer, so the final summary and the user read it from the file. Attempt counts on a failure signature and the oscillation count live in the note. Nothing else: the watcher's ledger records movement and messages, and this file is the state of what is or is not solved and what waits on a human.

**Name every row by its id, never by position.** The ids are `thread <full discussion id>`, `job <job name> @ pipeline <pipeline id>`, and `rebase !<iid>`; the watcher's messages, the actor's reports and this table all use them unchanged.

### The prompts

Keep them this short: the brief carries the rules, the ledger carries the state.

**Watcher spawn:**

```
MRs: https://git.example.com/group/service/-/merge_requests/123 (worktree /home/me/dev/service), https://git.example.com/group/pipelines/-/merge_requests/456 (worktree /home/me/dev/pipelines)
Report: pipeline finished, push, behind target, handshake, notes, verdict, approvals, merged/closed, quiet 2m after green, pipeline running 30m, idle 3h
Cadence: working
Self markers: <!-- sdlc:mr-babysit -->, <!-- sdlc:mr-open -->
Handshake: ready-for-review = not draft and ticket in "In Review"; back-to-work = ticket in "In Progress"
Ticket: TEAM-789 — work state "In Progress", review state "In Review", terminal states "Done", "Canceled"; load the <tracker skill name> skill before reading it
Ledger: ./.claude/review-report/<topic>.mr-watch.md
```

Omit the `Ticket:` line for `tracker: none`, and write the `Handshake:` line on the draft flag alone. Mid-run messages to the watcher use its own vocabulary: `add: <url> (worktree <path>)`, `drop: <url>`, `report: <event list>`, `cadence: working|waiting`, `report now`, `acted: <op> on <url> at <sha or timestamp>`, `stop`.

**Actor, triage batch** (the implementation subagent resumed, or a fresh one on `opus`):

```
First read ${CLAUDE_PLUGIN_ROOT}/skills/mr-babysit/references/actor-brief.md in full and load the skills it names.
Worktree /home/me/dev/service, source branch feat/orders-api, target master.
Triage, change nothing:
- pipeline 8812 on !123, dump at /tmp/glab-state/git.example.com/group__service/mr-123/pipeline/
- threads 7b3e01aa…, 2c8d44f1… on !123, dump at /tmp/glab-discussion/git.example.com/mr-123/
- rebase !456: the branch is 4 behind master; attempt it, push if clean, propose a row if it conflicts
Report one line per row, `<row id> proposed <disposition> — <evidence>`, plus every push with its verified SHA. Then end your turn.
```

**Actor, implementation batch:**

```
Same worktree, same brief. Implement these rows and post what is listed, nothing else:
thread 7b3e01aa… — `src/api/orders.py:88` returns 200 on a rejected order; raise the domain error and let the handler map it. Reply on the thread naming the SHA, then resolve.
job test:OrderSpec#total @ pipeline 8812 — total omits the discount line; the assertion is right and the code is wrong.
dismiss thread 2c8d44f1… — reply: line 88 already returns 409 through the handler; the finding reads the wrapper, not the handler. Then resolve.
Report one line per row, `<row id> fixed <sha>` / `could-not-fix <why>` / `posted <note id>` / `resolved`, the remote SHA you verified, and the verification per row. Then end your turn.
```

**Rules for the watchdog cron prompt:**
- **Arm the cron by calling it, not by printing it.** Pass 0 ends with a real `CronCreate` call, and your first note names the job id it returned. Writing the prompt line into the report as text arms nothing, and then a dead watcher is never noticed.
- **The prompt is plain text and never contains a slash command.** A `/sdlc:mr-babysit …` inside it re-enters the command on every firing and stacks a new run each time. Write it like: `Run the mr-babysit watchdog for MR !123 and !456 / ticket TEAM-789 using ledger ./.claude/review-report/<topic>.babysit.md`
- **Always name the explicit `!iid`s** and put no SHA in it.
- **Use a recurring cron, never a one-shot `ScheduleWakeup`.**
- **Never ask the user "should I continue?"** A running pipeline, open threads, or a push that just landed are the subagents' to carry on with.

## Messages and returns

### On a watcher message

The message names the MR, the events, the ids involved, the dump paths, and a scorecard line per MR. Decide what it means, dispatch, rewrite the ledger, and write a progress note of at most three lines. Never read the MR yourself.

- **`STATE_CHANGED` to merged or closed** → drop the MR from the set; if the set is empty, go to [Stopping](#stopping-instead-of-handing-over).
- **`HANDSHAKE back-to-work` while in handoff-wait** → the reviewer handed it back. Set `Mode: working`, message the watcher `cadence: working`, and treat the new threads as ordinary in-scope threads.
- **`PIPELINE_CHANGED` to `failed`** → a triage batch: `pipeline <id> on !<iid>` with the dump path from the message. A pipeline that ran on a superseded base is judged after the rebase.
- **`NOTES_CHANGED`** with threads the watcher classed as reviewer or human → a triage batch: `threads <ids> on !<iid>`. Threads under your own markers need nothing; a thread under another automation's marker is triaged like any reviewer's, and the actor's brief says which of those it may not resolve.
- **`BEHIND_CHANGED` to a non-zero count** → `rebase !<iid>` in the next batch. When the watcher says the MR is stacked on another branch, rebase the base MR first.
- **`HEAD_CHANGED`** → first match the SHA against the actor's last reported push; the watcher probes every minute and usually sees the run's own push before your ack reaches it. A SHA nobody in this run pushed is an author push from outside; a pipeline will follow.
- **`VERDICT_CHANGED` or `VERDICT_STALE`** → information for the next thread triage.
- **`QUIET`** with no row unfinished on any MR → the set may be settled; go to [Handoff](#handoff).
- **`PIPELINE_STUCK`** → a build that has not ended in 30 minutes. Write one line to the user naming the pipeline and the job it sits in, and dispatch nothing: a wedged build is not a failure signature, so it is neither retried nor fixed, and it is the user's to look at.
- **`IDLE`** → the watcher hit the cap the prompt named; go to [Stopping](#stopping-instead-of-handing-over).
- **`TICKET_CHANGED` to a terminal state** → the work moved past review; go to [Stopping](#stopping-instead-of-handing-over).
- **`READ_FAILED` or `DEPENDENCY MISSING`** → say so in the note; a missing helper goes to the user with the install command and a question.

**In a working cycle, a set already handed over while there is anything to rebase, triage or fix is taken back first**, per `teamwork:review-handshake`: your ticket move, then the batch opens with `reclaim !<iid>` for the actor's one-line comment, and you ack the watcher for both. A batch about to be implemented is work in progress too.

**One actor at a time.** While one is out, collect the next message's work and send it in the next batch. A rebase never runs while an implementation batch is out; it goes into the batch after it.

### On an actor return

1. **Read the report back before deciding anything.** A subagent that timed out or was killed taught you nothing — `Exit code 143`, "timed out" and "moved to the background" are not results, and a green is never carried forward on a dead subagent's word. After an implementation batch, run `git rev-parse origin/<source_branch>` yourself and confirm it matches the SHA the report names.
2. **Ack the watcher** for everything the actor pushed, posted, resolved or toggled, one `acted: <op> on <mr url> at <sha or timestamp>` line each, so the watcher does not report the run's own moves back to you as events.
3. **Decide every `proposed` row.** This is the judgment the command exists for, and it is yours alone:
   - **Approve a `fix`** when the evidence on the row supports it, the change is at the right layer (root cause, not symptom), and it does not contradict a fix already made this run. When the proposal is right about the problem but wrong about the change, approve it with your correction written into the batch.
   - **Approve a `dismiss`** when the reasoned disagreement holds — the finding misreads the code, is already covered, or would create a new problem. **Overturn it into a `fix`** when the actor was too quick and the finding is right after all. A severity tag is not a reason to approve either way. **A reviewer that re-raises a rule-and-file pair the ledger already holds as `dismissed` gets an `ask`, never a second dismissal**: the disagreement did not land, and a third round of it is whack-a-mole.
   - **Take an `ask` to the user**, in the progress note, without blocking anything else — dispatch the rest of the batch anyway. Never present the whole triage as options and wait for a go-ahead; only an `ask` reaches the user.
   - Whatever the disposition, **promise nothing on the MR**. The replies state facts — what changed, what SHA carries it, why a finding does not hold. `teamwork:review-handshake` holds the rule.
4. **Record the outcomes**: `fixed <sha>`, `could-not-fix`, `dismissed`, `ask`, and the attempt count on a failure signature. A `could-not-fix` row is yours to re-decide — a fresh `fix` proposal with a different approach, or an `ask` for the user.
5. **Dispatch the next batch**: the approved `fix` rows, the approved dismissals, and any reclaim or ready, to the actor as one implementation batch. Resume the same actor while it has context — it holds the code and the reasoning behind every row — and spawn a fresh one, pointed at the ledger, only when it runs out.
6. Post a progress note of **at most three lines** to the user.

### The watchdog is silent while the watcher lives

The heartbeat proves the watcher is alive; nothing proves it is dead, because a watcher that ran out of context, was killed, or is paused on a permission prompt sends nothing, and no message ever wakes you. The 30-minute cron is the one clock that fires without it. Each firing:

1. **Checks the watcher**: alive per `ListAgents`, and `Last message to parent` under 45 minutes old per the watcher's own ledger. Both hold → say nothing and end the turn. Either fails → message it (a message to an ended agent resumes it) or spawn a fresh one against its ledger, and say so in one line. That is a liveness read, never a substitute for a message.
2. **Checks the actor** against the ledger: approved rows with no actor out → dispatch them.

The progress line the user sees every 30 minutes comes from the watcher's `HEARTBEAT`, not from the cron: on every heartbeat write **one line, even when nothing changed** — for example "!123 pipeline running · fixing 2 rows, batch pushed at `a1b2c3d` · !456 handed over, idle 40m", composed from the ledger and the scorecard in the message. A run that says nothing for an hour is a dead run.

## Handoff

### The handoff condition

Hand the set over when **every MR** satisfies **all** of these, read off the watcher's scorecard and the ledger:

1. The pipeline is **green** (`success`) on the current head. `canceled`, `manual` and `skipped` are not green.
2. It has been **≥2 minutes quiet** — the watcher's `QUIET` event: a green pipeline on the current head with no note movement for two minutes, which gives an AI reviewer time to weigh in on the final commit.
3. Every actionable comment has a reply, and every thread the actor handled is resolved. Watch threads carry a reply and stay unresolved, which is the settled state for them.
4. The only remaining open threads, if any, are `ask` rows or skips, watch threads already answered, or human threads left for the human to close.
5. **No row is unfinished** — no `ask`, no `approved`, no `fixing`, no `could-not-fix`. Every one of those means the change is not finished, so the ticket stays in the work state — and an MR never handed over stays draft — and you hand back to the user instead.
6. The branch is **not behind its target branch** — or the divergence provably does not touch this MR. Master often moves faster than a long pipeline finishes, so a rebase-then-wait cycle can never converge. The actor's rebase report gives the two file sets and whether they intersect; hand over behind **only** when they do not, and say it in the handover line: "4 commits behind master, docs-only, no overlap with this MR". Any overlap means rebase first and let the watcher report the resulting pipeline.

### Hand the ball over

Hand over per `teamwork:review-handshake`: an implementation batch of `ready !<iid>` for every MR in the set, then your ticket move, **once**, when every MR on that ticket qualifies. One MR going green while its sibling is still red is not a handover.

Then ack the watcher for whatever moved, message it `cadence: waiting`, and set `Mode: handoff-wait`. Do **not** stop: the reviewer has the ball.

### Handoff-wait

Nothing polls. The watcher keeps watching in the waiting cadence and messages you on a handshake flip, new notes, the merge, or the idle cap; every heartbeat gets its one line, for example "!123 handed over, waiting on reviewer, idle 1h10m". No actor runs in handoff-wait: with the table settled, there is nothing to dispatch.

**Each message does one of four things:**

- **`HANDSHAKE back-to-work`** → the reviewer handed it back. Set `Mode: working`, message the watcher `cadence: working`. New reviewer threads are ordinary in-scope threads, and their triage comes back to you like any other.
- **`HEARTBEAT` with the flags unmoved** → nothing moved. Write the one line, naming how long the set has been idle.
- **Every MR merged or closed, or the ticket reached a terminal state** → stop the watcher, confirm the actor has returned, delete the cron job, report, and stop for good.
- **`NOTES_CHANGED` while the flags did not move** → a reviewer is mid-review, and a comment is not a hand-back. Write one line as an FYI — "!123 handed over, 3 new comments since 14:02, reviewer still active" — and keep waiting. Take the work back on one of two signals only: the handshake flips (the bullet above), or the newest comment is **at least 30 minutes old** with the flags still unmoved, which you read off the watcher's next heartbeat — the reviewer left comments and walked away without handing over. On that second signal set `Mode: working`, move the ticket to the work state yourself, dispatch the thread triage with a `reclaim !<iid>` row so the actor says why on the MR, and message the watcher `cadence: working`.

**Idle cap: 3 hours.** The watcher reports `IDLE` when nothing has moved for the cap its prompt named. End the run: stop the watcher, confirm the actor has returned, delete the cron job, and report. Say plainly that it stopped on an **idle timeout, not on a merge**, name what is still outstanding, and name the way back in — running `/sdlc:mr-babysit` again picks the same set up.

The user can opt out of the wait with an explicit "stop after handoff". Then the handover is the last thing this command does — report and end, stopping the watcher, deleting the cron job and leaving no subagent running.

### Stopping instead of handing over

**Stop and hand back to the user** on any of: all MRs merged/closed; a rebase conflict that encodes a genuine product/design decision; a CI failure triaged as `ask`, or a failure signature that hit its 2-attempt cap and is still red; a `could-not-fix` row with no way forward; a reply or resolve that kept failing after a retry; oscillation (this batch's fix contradicting the last one's); or an outstanding `ask` with nothing else left to solve. A halt on one MR doesn't have to halt the others — keep babysitting the rest and report the one that needs you.

Whenever you stop this way, the set stays back-to-work, per `teamwork:review-handshake`.

**Leave nothing running.** A stop is complete only when the watcher has acknowledged `stop` and ended its turn, the actor has returned and its report has been read back, and the cron job is deleted. An actor still working its batch is allowed to finish and return; dispatch nothing after a halt. Never stop while a subagent is alive, and never report a halt on a subagent you did not read back.

Present a final summary: the per-MR scorecard, what was fixed and pushed with SHAs, each MR's state, whether you handed over or stopped, and — as a clear list — every `ask` row from the ledger (thread location + quoted comment + your suggested reply or change), and ask the user how to proceed.

## Scope

$ARGUMENTS
