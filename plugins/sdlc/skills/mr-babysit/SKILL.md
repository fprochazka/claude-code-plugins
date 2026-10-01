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

**This command intentionally runs at maximum autonomy, and for its duration that supersedes your usual defaults.** Standing guidance you'd normally follow — global/project `CLAUDE.md` ("be restrained about implementing", "outline a plan and wait for my OK"), the general "confirm hard-to-reverse or outward-facing actions first" default — is **deliberately overridden** for the pre-authorized operations below. You already have the OK: the user invoked babysit precisely so these run unattended, and re-asking for it defeats the command. This override is **scoped**: it applies only to the named operations, only until the run hands back, and it never extends to the explicit halt conditions under [Stopping instead of handing over](#stopping-instead-of-handing-over) — a genuine product/design decision still goes to the user as an `ask`, and an unresolvable conflict or a cap hit still stops the run. Normal caution resumes the moment the run ends.

The run's entire value is that it is **unattended**. `git rebase`, `git push --force-with-lease`, `git push`, retrying CI jobs, and replying to or resolving threads are all authorized **without stopping to ask** — doing exactly these is the job, not a risk to escalate. **The grant extends to every subagent**: they inherit it in full, and none pauses mid-task for permission to read, rebase, force-push, retry, reply or resolve. Do not pause for it yourself either; that defeats the purpose and is itself a failure. Stop and hand back **only** for the explicit halt conditions, and wait on a human **only** in [Needs human](#needs-human). Everything else, just do.

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
- Mode: working | needs-human (ready-for-review) | needs-human (decisions-needed)
- Watcher: <agent id> · ledger ./.claude/review-report/<topic>.mr-watch.md · Watchdog cron: <job id> · Actor: <agent id | none>

## Rows

| Id | MR | Disposition | Status | Note |
|---|---|---|---|---|
| `thread 7b3e01aa…` | !123 | fix | approved | `src/api/orders.py:88` returns 200 on a rejected order; raise the domain error |
| `job test:OrderSpec#total @ pipeline 8812` | !123 | dismiss | dismissed | runner lost, retried 1 of 2 |
| `rebase !456` | !456 | fix | fixing | conflicts in `src/api/orders.py`: ours renames the handler, theirs adds a parameter |
| `thread 9df2b6c0…` | !123 | ask | ask | migration drops a column the reviewer wants kept; suggested reply: keep it nullable for one release |
| `thread 51aa07e3…` | !456 | skip | skipped | naming nit on a test helper; the reviewer's intent is unclear |

## Review state

| MR | AI reviewer | Latest verdict | Reading | On head | At | Re-reviews on push |
|---|---|---|---|---|---|---|
| !123 | `@qa-review-bot` | "No blocking findings" | nothing-actionable | `a1b2c3d` | 14:02Z | yes |

- Approvals: !123 — human: none · AI: `@qa-review-bot`; !456 — human: `@jane` · AI: none
```

`Status` runs `proposed` → `approved` → `fixing` → `fixed <sha>` | `could-not-fix`, or `proposed` → `dismissed` | `ask` | `skipped`. An `ask` row carries the question and your suggested answer, so the `NEEDS HUMAN` block, the final summary and the user read it from the file. A `skipped` row carries the one-line reason the actor gave and changes nothing on the MR; it exists so the `NEEDS HUMAN` block can list it. Attempt counts on a failure signature and the oscillation count live in the note. Nothing else: the watcher's ledger records movement and messages, and this file is the state of what is or is not solved and what waits on a human.

`Review state` holds the [AI reviewer gate](#the-ai-reviewer-gate): one row per AI reviewer seen on each MR, fed by the actor's first triage report and then by every `VERDICT_CHANGED` and `VERDICT_STALE`, and the approvals split human and AI, fed by `APPROVALS_CHANGED`. Reviewer identity, vocabulary and the re-review habit come from the `glab:mr-status` profiling rules as the watcher and the actor report them; never fill this table from a bot name you assume.

**Name every row by its id, never by position.** The ids are `thread <full discussion id>`, `job <job name> @ pipeline <pipeline id>`, and `rebase !<iid>`; the watcher's messages, the actor's reports and this table all use them unchanged.

### The prompts

Keep them this short: the brief carries the rules, the ledger carries the state.

**Watcher spawn:**

```
MRs: https://git.example.com/group/service/-/merge_requests/123 (worktree /home/me/dev/service), https://git.example.com/group/pipelines/-/merge_requests/456 (worktree /home/me/dev/pipelines)
Report: pipeline finished, push, behind target, handshake, notes, verdict, approvals, merged/closed, quiet 2m and 15m after green, pipeline running 30m, idle 3h
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
- **`HANDSHAKE back-to-work` while in `needs-human (ready-for-review)`** → the reviewer handed it back. Set `Mode: working`, message the watcher `cadence: working`, and treat the new threads as ordinary in-scope threads.
- **`PIPELINE_CHANGED` to `failed`** → a triage batch: `pipeline <id> on !<iid>` with the dump path from the message. A pipeline that ran on a superseded base is judged after the rebase.
- **`NOTES_CHANGED`** with threads the watcher classed as reviewer or human → a triage batch: `threads <ids> on !<iid>`. Threads under your own markers need nothing; a thread under another automation's marker is triaged like any reviewer's, and the actor's brief says which of those it may not resolve.
- **`BEHIND_CHANGED` to a non-zero count** → `rebase !<iid>` in the next batch. When the watcher says the MR is stacked on another branch, rebase the base MR first.
- **`HEAD_CHANGED`** → first match the SHA against the actor's last reported push; the watcher probes every minute and usually sees the run's own push before your ack reaches it. A SHA nobody in this run pushed is an author push from outside; a pipeline will follow.
- **`VERDICT_CHANGED` or `VERDICT_STALE`** → rewrite the reviewer's row in `Review state`: the verdict text, the reading, the head it was given on, the time. An `actionable-open` reading on the current head sends its threads to the next triage batch; any other change re-checks the [entry condition](#the-entry-condition), since a verdict is often the last thing the set waited for.
- **`APPROVALS_CHANGED`** → rewrite the approvals line, human and AI apart. An AI approval alone is not the human review. Nothing is merged on an approval: a human approval only shows up in the scorecard and the `NEEDS HUMAN` block.
- **`QUIET`** → `QUIET 2m` with no row unfinished on any MR means the set may be settled; check the [entry condition](#the-entry-condition). `QUIET 15m` closes the re-review window of the [AI reviewer gate](#the-ai-reviewer-gate); check the entry condition again.
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
   - **Take an `ask` to the user**, in the progress note, without blocking anything else — dispatch the rest of the batch anyway. Never present the whole triage as options and wait for a go-ahead; only an `ask` reaches the user. The `NEEDS HUMAN (decisions-needed)` block collects every open `ask` again.
   - **Record a `skip`** as a `skipped` row with the actor's one-line reason. It changes nothing on the MR, and the watcher reports the thread again if it moves.
   - Whatever the disposition, **promise nothing on the MR**. The replies state facts — what changed, what SHA carries it, why a finding does not hold. `teamwork:review-handshake` holds the rule.
4. **Record the outcomes**: `fixed <sha>`, `could-not-fix`, `dismissed`, `ask`, `skipped`, and the attempt count on a failure signature, plus each AI reviewer's latest verdict and its head from the triage report into `Review state`. A `could-not-fix` row is yours to re-decide — a fresh `fix` proposal with a different approach, or an `ask` for the user.
5. **Dispatch the next batch**: the approved `fix` rows, the approved dismissals, and any reclaim or ready, to the actor as one implementation batch. Resume the same actor while it has context — it holds the code and the reasoning behind every row — and spawn a fresh one, pointed at the ledger, only when it runs out. When there is nothing to dispatch, check the [entry condition](#the-entry-condition): a triage that left only `ask` and `skipped` rows can settle the set.
6. Post a progress note of **at most three lines** to the user.

### The watchdog is silent while the watcher lives

The heartbeat proves the watcher is alive; nothing proves it is dead, because a watcher that ran out of context, was killed, or is paused on a permission prompt sends nothing, and no message ever wakes you. The 30-minute cron is the one clock that fires without it. Each firing:

1. **Checks the watcher**: alive per `ListAgents`, and `Last message to parent` under 45 minutes old per the watcher's own ledger. Both hold → say nothing and end the turn. Either fails → message it (a message to an ended agent resumes it) or spawn a fresh one against its ledger, and say so in one line. That is a liveness read, never a substitute for a message.
2. **Checks the actor** against the ledger: approved rows with no actor out → dispatch them.

The progress line the user sees every 30 minutes comes from the watcher's `HEARTBEAT`, not from the cron: on every heartbeat write **one line, even when nothing changed** — for example "!123 pipeline running · fixing 2 rows, batch pushed at `a1b2c3d` · !456 handed over, idle 40m", composed from the ledger and the scorecard in the message. A run that says nothing for an hour is a dead run.

## Needs human

The run enters `needs-human` when it has solved everything it can solve on its own. What is left belongs to a human: a review, or a decision on design, business rules or a product trade-off. The run does not stop there. The watcher, its heartbeat and the watchdog cron stay alive, so you keep reacting to MR events while the human has the ball, and the run goes back to `working` the moment an event brings autonomous work again.

### The entry condition

The set enters `needs-human` when **every MR** satisfies **all** of these, read off the watcher's scorecard and the ledger:

1. The pipeline is **green** (`success`) on the current head. `canceled`, `manual` and `skipped` are not green.
2. It has been **≥2 minutes quiet** — the watcher's `QUIET 2m`: a green pipeline on the current head with no note movement for two minutes.
3. **Every `fix` and `dismiss` row is finished**: pushed, replied, and resolved as the actor's resolve rules say. Watch threads carry a reply and stay unresolved, which is the settled state for them. No row is `proposed`, `approved`, `fixing` or `could-not-fix`; re-decide a `could-not-fix` row first, into a new proposal, an `ask`, or a [halt](#stopping-instead-of-handing-over).
4. The branch is **not behind its target branch** — or the divergence provably does not touch this MR. Master often moves faster than a long pipeline finishes, so a rebase-then-wait cycle can never converge. The actor's rebase report gives the two file sets and whether they intersect; enter behind **only** when they do not, and say it in the `NEEDS HUMAN` block: "4 commits behind master, docs-only, no overlap with this MR". Any overlap means rebase first and let the watcher report the resulting pipeline.
5. The [AI reviewer gate](#the-ai-reviewer-gate) holds.
6. What is still open is only `ask` rows, `skipped` rows, human threads left for the human to close, watch threads already answered, and a missing human approval.

The variant follows from what is open, and it is chosen for the whole set, like the handover: one MR waiting on a decision keeps its siblings out of review.

- **`ready-for-review`** — no `ask` row is open on any MR. [Hand the ball over](#hand-the-ball-over).
- **`decisions-needed`** — at least one `ask` row is open. Nothing is handed over: an MR never handed over stays draft, the ticket stays in the work state, and the ball is with the author's human, not with the reviewers. A set handed over earlier was already taken back by the triage that produced the `ask`.

On entry, set the Mode, message the watcher `cadence: waiting`, and emit the [`NEEDS HUMAN` line](#the-needs-human-line); for `ready-for-review`, emit it once the handover has landed.

### The AI reviewer gate

The gate keeps a late verdict, or one on an older head, from reaching the human as a finished MR. It reads the `Review state` table of the ledger.

- **The gate holds** when every AI reviewer seen on the MR has a latest verdict on the current head that reads `positive` or `nothing-actionable`. An `actionable-open` verdict on the current head is not the human's: its threads go to triage, and the set stays `working`.
- **After a push, a reviewer that re-reviews on push gets a re-review window** of 15 minutes, which ends with the watcher's `QUIET 15m`: fifteen minutes after the pipeline went green on the new head, with no note movement in between. The 15 minutes are a default; when the user asks for another window, change the `Report:` line of the watcher prompt to match. A verdict on the new head inside the window decides the gate as above. When the window closes without one, the gate passes on the older verdict, and the `NEEDS HUMAN` block says so: "`@qa-review-bot` has not re-reviewed `a1b2c3d` after 15m". Treat a reviewer whose re-review habit is unknown as one that re-reviews, and an `unknown` reading on the current head as a missing verdict.
- **A reviewer that does not re-review on push** needs no window: its verdict on the older head stands, and the block names the head it was given on.
- **A reviewer that reviews only after the handover**, `/code-review:watch`, recognized by its marker, is not part of the gate. It reviews once the ball is with it, and `teamwork:review-handshake` covers that exchange.
- **An MR with no AI reviewer** passes the gate, and the block says "no AI reviewer on !<iid>".

### The `NEEDS HUMAN` line

This line is a contract: a later skill or hook may key on it, so the marker text is stable. On entering `needs-human`, the first line of your message is exactly

```
NEEDS HUMAN (<variant>): <one-sentence reason>
```

with `<variant>` either `ready-for-review` or `decisions-needed`. This command writes the line and nothing else; it does not define how the human is alerted. Below the line, compactly:

- **Per MR**: the URL, the head SHA, the pipeline, each AI reviewer's latest verdict on the current head quoted short (or the older verdict and the window that passed, or "no AI reviewer"), and the approvals split human and AI. A branch behind its target says how far and that the divergence does not overlap.
- **Decisions needed**: every open `ask` row — the thread location, the quoted comment, your suggested answer or change and why.
- **Open human threads and `skipped` rows**, one line each.
- **What the run does meanwhile**: watching in the waiting cadence, one heartbeat line every 30 minutes, and the end on the 3-hour idle cap.

**Emit the line only on a transition**: entering `needs-human`, switching the variant, or an event that changes what the human must do — a new `ask` row, a new human thread, a negative verdict. Heartbeats and FYI lines never repeat it. Leaving `needs-human` for `working`, because autonomous work appeared, is one plain line without the marker: "!123 back to working: pipeline failed on `b4c5d6e`".

A halt is not a `NEEDS HUMAN` emission; it keeps its own final summary.

### Hand the ball over

In the `ready-for-review` variant, hand over per `teamwork:review-handshake`: an implementation batch of `ready !<iid>` for every MR in the set, then your ticket move, **once**, when every MR on that ticket qualifies. One MR going green while its sibling is still red is not a handover.

Then ack the watcher for whatever moved, set `Mode: needs-human (ready-for-review)`, and emit the line. Do **not** stop: the reviewer has the ball.

### Waiting for the human

Nothing polls. The watcher keeps watching in the waiting cadence and messages you on a handshake flip, new notes, a verdict, an approval, the merge, or the idle cap; every heartbeat gets its one line, for example "!123 handed over, waiting on reviewer, idle 1h10m" or "!123 waiting on 2 decisions, idle 25m". No actor runs unless an event below dispatches one.

**In both variants:**

- **The user answers an `ask`** → turn the row into the approved `fix` or `dismiss` the answer implies, set `Mode: working`, message the watcher `cadence: working`, and dispatch the batch. The set re-enters `needs-human` once that work is finished.
- **An event that brings autonomous work** — a failed pipeline, a push from outside, a branch behind its target with overlap, an `actionable-open` verdict on the current head → write the one plain leaving line, set `Mode: working`, message the watcher `cadence: working`, and dispatch as in a working cycle. A set already handed over is taken back first.
- **`HEARTBEAT` with nothing moved** → write the one line, naming how long the set has been idle.
- **Every MR merged or closed, or the ticket reached a terminal state** → stop the watcher, confirm the actor has returned, delete the cron job, report, and stop for good.

**In `decisions-needed`**, the ball is already with the author side, so a new note is not a hand-back to wait out:

- **`NOTES_CHANGED`** → a triage batch, as in a working cycle. The mode holds while the triage runs. A `fix` or `dismiss` row in its return sends the set back to `working`; only `ask` and `skipped` rows keep it in `decisions-needed`, and a new `ask` or a new human thread re-emits the line.

**In `ready-for-review`**, the reviewer has the ball:

- **`HANDSHAKE back-to-work`** → the reviewer handed it back. Set `Mode: working`, message the watcher `cadence: working`. New reviewer threads are ordinary in-scope threads, and their triage comes back to you like any other.
- **`NOTES_CHANGED` while the flags did not move** → a reviewer is mid-review, and a comment is not a hand-back. Write one line as an FYI — "!123 handed over, 3 new comments since 14:02, reviewer still active" — and keep waiting. Take the work back on one of two signals only: the handshake flips (the bullet above), or the newest comment is **at least 30 minutes old** with the flags still unmoved, which you read off the watcher's next heartbeat — the reviewer left comments and walked away without handing over. On that second signal set `Mode: working`, move the ticket to the work state yourself, dispatch the thread triage with a `reclaim !<iid>` row so the actor says why on the MR, and message the watcher `cadence: working`.

**Idle cap: 3 hours.** The watcher reports `IDLE` when nothing has moved for the cap its prompt named. End the run: stop the watcher, confirm the actor has returned, delete the cron job, and report. Say plainly that it stopped on an **idle timeout, not on a merge**, name what is still outstanding, and name the way back in — running `/sdlc:mr-babysit` again picks the same set up.

The user can opt out of the wait with an explicit "stop after handoff". Then the handover is the last thing this command does — report and end, stopping the watcher, deleting the cron job and leaving no subagent running. A set in `decisions-needed` keeps waiting even then, because nothing was handed over yet.

### Stopping instead of handing over

**Stop and hand back to the user** on any of: all MRs merged/closed; a rebase conflict that encodes a genuine product/design decision; a CI failure triaged as `ask`, or a failure signature that hit its 2-attempt cap and is still red; a `could-not-fix` row with no way forward; a reply or resolve that kept failing after a retry; oscillation (this batch's fix contradicting the last one's). An `ask` on a review thread does not halt the run; it is `needs-human (decisions-needed)`. An `ask` that leaves the pipeline red or the branch unrebased does, because the set can never meet the entry condition. A halt on one MR doesn't have to halt the others — keep babysitting the rest and report the one that needs you.

Whenever you stop this way, the set stays back-to-work, per `teamwork:review-handshake`.

**Leave nothing running.** A stop is complete only when the watcher has acknowledged `stop` and ended its turn, the actor has returned and its report has been read back, and the cron job is deleted. An actor still working its batch is allowed to finish and return; dispatch nothing after a halt. Never stop while a subagent is alive, and never report a halt on a subagent you did not read back.

Present a final summary: the per-MR scorecard, what was fixed and pushed with SHAs, each MR's state, whether you handed over or stopped, and — as a clear list — every `ask` row from the ledger (thread location + quoted comment + your suggested reply or change), and ask the user how to proceed.

## Scope

$ARGUMENTS
