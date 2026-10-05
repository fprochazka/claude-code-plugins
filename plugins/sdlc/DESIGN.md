# sdlc: design

Read this before you change the plugin. It records why the plugin exists, what it must not become, and what was already tried. A change that contradicts a principle or reverses a decision needs the maintainer's explicit approval and a new entry under [Decisions](#decisions).

## Purpose

A product engineer gets a vague problem, often as a ticket. Before anyone can discuss a solution, someone has to establish how the system behaves today, and that knowledge is mostly for the agent's benefit. Then the change has to be designed, implemented, put up for review, and driven through CI and review comments until a human can look at it. Without written instructions, the agent jumped to implementation, wrote chat replies too long to read, stopped to ask permission for routine git operations, said it would do something and then stopped, and declared an MR done while review findings were still open.

The plugin gives each stage of that one task its own skill: `pre-plan` and `brief-next-steps` gather context and state the proposal, `ticket-new` files the ticket, `write-plan` plans and runs the implementation, `mr-open` and `mr-babysit` take the MR to review, and `ticket-attach-docs` and `wrap-up` put the record on the ticket. The skills started as personal commands in `~/.claude/commands/`: `ticket-new` (2026-03-04), `pre-plan` (2026-05-20), `open-mr` (2026-05-27), `write-plan` (2026-06-07), and `brief-next-steps` (2026-08-05). `mr-babysit` started as `glab-mr:babysit` on 2026-07-05. The plugin was created on 2026-08-06 in session `d75afcd8-ba88-42d7-8d80-ec3e349691cf`.

## Goals

- Context first: the agent reads the ticket and the code before the user discusses a solution, and it writes what it learned to files that the plan and the implementation build on.
- Each decision that the user owes is stated up front, with a recommended answer and the reason it wins over the alternatives.
- After the user approves the plan, the run finishes without supervision: implementation, validation, MR, CI, and review comments. It stops only for a product decision or a step that is damaging or hard to reverse.
- The MR reaches the human only when everything the agent can solve alone is solved: the pipeline is green on the current head and every AI reviewer is satisfied with that head.
- The ticket holds the record: the Why, the plan and research documents, the production checks, and the follow-ups.
- Text that a person reads is short: a briefing instead of the argument, a one-screen MR description, a dense wrap-up comment.

## Non-goals and scope

- **One task.** One engineer, one problem, one ticket, one branch, one MR set. The maintainer: "its not meant for starting fresh projects or planning long projects into many tickets". Work that spans many tickets gets new skills (probably with a `task-` prefix), not a stretched version of these.
- **No specific tracker or chat tool.** Skills name no tracker CLI. The tracker comes from `teamwork:workflow-identify`, and the agent then loads the skill for it. `mr-babysit` is the exception: it is GitLab-only, because its loop is built on `glab`, `glab-discussion` and `glab-pipeline`.
- **Not the reviewer side.** `code-review:watch` reviews and never changes code. `mr-babysit` is its mirror. The handover protocol and the state names live in `teamwork`. Watching an MR lives in `glab:mr-watch`. sdlc points at them and does not restate them.
- **No human alerting.** `mr-babysit` emits one fixed `NEEDS HUMAN (<variant>): <reason>` line. How the human is notified is left to a hook or another skill. A separate attention skill was postponed on 2026-10-01, not rejected.
- **No discovery.** `mr-babysit` works on the MRs that the user named or that the session created. `wrap-up` reports what the session knows and never looks a status up.

## Principles

1. **Name no tool, load the skill for it.** A skill says "the issue tracker" or "Slack", never the name of a tracker CLI. The agent resolves the tracker with `teamwork:workflow-identify` and loads the matching skill. The maintainer wants the plugin to work outside his own setup: "every time you talk about issue trackers, say it so that it is clear that the agent needs to infer what the team is using". Hard dependencies are other plugins, never a vendor's CLI. The exception is `mr-babysit`, which depends on GitLab.
2. **Results go to files, and subagents return a path.** Context, briefings, plans, ticket drafts and the babysit ledger live under `./.claude/plans/` or `./.claude/review-report/` in the worktree. Temporary payloads go to the scratchpad. A file survives the session, lets a fresh context window pick up from the plan on, and keeps the orchestrator's context small. A subagent gets the path of the file plus what to focus on, never chunks of the file pasted into its prompt.
3. **The orchestrator decides, subagents do the work.** The main session does not edit code, even to fix a small problem between two steps. It sends the finding back to the subagent that did the work. Prefer resuming a subagent that already holds the context over starting a fresh one, because a fresh one explores the repository again. This applies to the `write-plan` implementation subagent, the `ticket-attach-docs` inventory subagent, and the `mr-babysit` actor. Validators are the exception. They always start cold, with only the plan and its intention, "we want the validation subagents to be finding flaws, not confirming the bias of the main orchestrator".
4. **Once the plan is approved, do not stop to ask.** Make mechanical decisions from data and continue. Park a product decision and continue with the steps it does not block. Stop only when a step would be damaging or hard to reverse. The maintainer: "I'm not always present at the keyboard". During its loop, `mr-babysit` deliberately overrides the cautious defaults in the user's own instructions: rebase, force-push with lease, push, CI retry, reply and resolve are pre-authorized for every subagent. A stall is a defect. An agent that announced work and then stopped is why `write-plan` arms a 30-minute "continue the plan" cron.
5. **Every open decision comes with a recommendation.** The user sees the recommended approach, why it wins, and the rejected alternatives with their reasons. A decision the user already made is never offered again ("Do it, do not offer me options").
6. **Report what the session established, and promise nothing.** `wrap-up` reports only what the session knows. A ticket is written as if nothing is implemented yet, even when the work is done. No comment commits anyone to future work.
7. **Point at the shared skill, do not restate it.** `git:git-workflow`, `prose:technical-writing`, `teamwork:review-handshake`, `glab:mr-status` and `diagrams:mermaid` are loaded by name. When a rule moves into a shared skill, the source skill must get shorter. The maintainer on the teamwork extraction: "if we haven't reduced the size ... of the skills where it was extracted from then what was the point".
8. **Short skill text.** A skill holds the rules, not the reasons for each rule. The reasons belong in this file and in the commit messages. Where a command sits in the flow belongs in its description, not in its instructions. The README leaves out implementation details.
9. **Missing dependency: say so, do not fall back.** When `glab-discussion` or `glab-pipeline` is missing, the run says which one and asks the user to install it. It does not improvise with raw `glab`. Check a capability by trying the call and inspecting the failure, not with a version check up front. A transient failure is retried once. A persistent failure is reported.
10. **Arguments sit under a `## Scope` heading.** The body refers to "the Scope above" and never to `$ARGUMENTS`.

### pre-plan

- It gathers context for three later uses: discussing the solution, writing the plan, and implementing. It never plans and never implements.
- The ticket is optional. A ticket reference reads the ticket, free text skips the ticket phase, and an empty scope uses the conversation. This is why the name has no `ticket-` prefix.
- The ticket subagent reads the ticket and everything it links to. For a linked MR it reads the diff stat, never the diff, and it never opens the codebase. Whether a diff is relevant is decided later, from the code map. The user's scope constraints go into every subagent prompt verbatim.
- One surface map comes first, then one deep dive per subdomain. The phases never overlap. Deep dives that barely overlap may run in parallel. Dives that overlap run one after another, so each dive can change the scope of the next.
- It ends by running `brief-next-steps`, so the chat reply is the conclusion and the long file stays the argument.

### brief-next-steps

- The briefing is the conclusion, not the argument. It is short, with no minimum length and a ceiling of about 170 lines. Details stay in the pre-plan. The maintainer has repeated this in several sessions: "the briefing is supposed to be short, details go into the non-briefing pre-plan".
- It never explores for new material, because then it would be pre-plan. The orchestrator writes it, because only the orchestrator has seen the session.
- An existing briefing is overwritten, because a briefing is a snapshot of the current state.
- Under each decision the user owes, it shows only the strongest rejected alternative and points at the pre-plan for the rest.

### write-plan

- A plan step is about one atomic commit. A phase can hold several commits. Validation runs at phase boundaries and after the last step.
- One persistent implementation subagent does the steps, one per message, and keeps its exploration in context. A fresh one starts only when the context runs out or when the plan swaps the model at a phase boundary. The plan names the model: opus by default, fable for hard reasoning.
- The subagent stages its work and does not commit. The orchestrator checks every step, either directly or through a cold validation subagent, as the plan decided per step. The orchestrator then commits. Staged work costs nothing to reject, and `git diff --cached` shows it in one call. The check is guided by the subagent's report on what is tricky, not by a read of the whole diff, which can include large snapshot files.
- Plan mode is entered only for the final writing. Plan mode restricts permissions and blocked the explorations needed to settle the open decisions.
- The plan opens with a Sources line that points at the pre-plan files and carries only the delta since then.
- After the final validation the plan continues into `mr-open` and `mr-babysit` without asking, unless the user said they will handle the MR. Its own cron is deleted before `mr-babysit` starts, so that only one watcher runs.

### ticket-new

- It drafts from a conversation already held. It does not interview the user.
- The ticket is written from the product side: business context and acceptance criteria. It names no solution, at most the relevant areas of the code.
- Status follows the real state of the work. When code exists, the ticket is in progress and assigned to the user driving the session. Otherwise it goes to the backlog. The body still reads as if nothing is implemented yet.
- The orchestrator writes the body to a file. A sonnet subagent looks up the tracker identifiers, creates the ticket from that file byte for byte, and reports the final metadata. The user sees a short summary and the path, not the recited draft.

### mr-open

- The description fits on one screen. The Why goes into the ticket: into the body when the body is empty, as a comment when it already has content. If the ticket is missing the Why, fix the ticket, not the description.
- The reading guide for the reviewer, the release procedure and the measured results go into separate MR comments, so that each one can be discussed in its own thread. The description links the release comment as must-read.
- A diagram is the model's call, never forced, and it goes in a comment, not the description.
- Every comment ends with `<!-- sdlc:mr-open -->`.

### mr-babysit

- **Roles.** The command decides and keeps the ledger. `glab:mr-watch` watches and reports events. One actor triages and implements. The actor is the plan's implementation subagent while it is alive, otherwise a fresh opus subagent. Its rules live in `references/actor-brief.md`. Nobody in the run polls or sleeps.
- **Triage and implementation are separate batches.** Triage proposes `fix`, `dismiss`, `ask` or `skip` for each failed job and open thread. The orchestrator approves the proposals and sends the approved rows back to implement, post and push. Each batch is pushed, so progress shows on the MR.
- **Review feedback is judged, never rubber-stamped.** AI findings, nitpicks included, are not left open when the run claims to be done. A dismissal that a reviewer raises again becomes an `ask`, never a second dismissal.
- **Thread rules.** A thread is in scope unless its latest note is the run's own (`<!-- sdlc:mr-babysit -->`, or `<!-- sdlc:mr-open -->` from the same session). Any other marker means other automation. No marker means a person or a bot. A `code-review:watch` thread gets a fix and a reply but is never resolved. A human's thread is resolved only when the reply squarely answers it. Pending drafts are ignored, and the run never writes draft comments on its own MR.
- **Handover.** On the first handover the draft flag flips. From then on the ticket state alone shows whose turn it is. New comments after the handover are an FYI, not a reason to take the work back. Approval is always a human act.
- **Needs human.** The run enters `needs-human` only when the pipeline is green on the current head, every fix and dismissal row is done, and each AI reviewer's latest verdict on the current head is positive or has nothing actionable. A reviewer that re-reviews on push gets a 15-minute quiet window. The turn ends with plain text, not AskUserQuestion: a question blocks the session for as long as the human is away, and the prompt cache goes cold.
- **Pushes.** Before every push the run checks again that the MR is open. After the push it compares the remote SHA instead of trusting the push output.
- **Retries.** A flaky job is retried at most twice and reported loudly, so the user can decide later whether to fix it.
- **Rebase conflicts.** The run resolves them without asking, rebuilding the MR's intended change on the target branch. It stops only when the conflict encodes a product decision.

### ticket-attach-docs and wrap-up

- Documents are attached late, from `wrap-up`, to avoid churn while they still change. The carrier depends on what the tracker offers: a document, an attachment, or a comment. The skill proposes before it acts.
- A sonnet subagent takes the inventory of what the ticket holds. The same subagent is resumed for the upload, so it does not load the ticket again.
- `wrap-up` runs in the session that did the work, because the findings that the diff does not show live only there. Production numbers are the core of the comment. The comment is dense, at most about 50 lines, and is split into several comments when one would bury its best parts. It links an MR only when it discusses several MRs separately.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-03-04 | `ticket-new` drafts from the conversation, with no interview | The maintainer asks for a ticket after the discussion, when the context is already there |
| 2026-03-05 | `ticket-new` creates tickets in the backlog | Reversed on 2026-08-06: status follows the real state of the work |
| 2026-03-21 | A ticket never mentions implementation status | The ticket describes the problem, not the branch |
| 2026-05-20 | `pre-plan`, not `ticket-research`, `ticket-context` or `ticket-pre-planning` | A ticket is optional; a `ticket-` prefix made it look required |
| 2026-05-20 | Deep dives run one after another | Reversed on 2026-08-24: dives that barely overlap run in parallel to save time |
| 2026-05-20 | Context files go to `./.claude/plans/`, not `/tmp` | Project-relative, and they survive the session |
| 2026-06-07 | The implementation subagent stages and the orchestrator commits | Staged work costs nothing to reject and shows in one `git diff --cached`. The assistant first proposed committing; the maintainer asked it to reconsider efficiency |
| 2026-06-07 | `write-plan` restates no `git-workflow` rules | The skill is loaded by name; only the step-to-commit mapping stays |
| 2026-06-07 | Enter plan mode first and write the plan inside it | Reversed on 2026-08-24: plan mode is entered only for the final writing |
| 2026-06-07 | The protocol covers only the path up to the user's review | Reversed on 2026-08-14: the plan continues into `mr-open` and `mr-babysit` |
| 2026-07-02 | `babysit` does not stop for judgment calls. It solves what it can and asks at the end | The maintainer wants solved work, not questions in the middle of a run |
| 2026-07-02 | No Monitor tool, a `/loop` every 2 minutes, and a one-sentence re-check prompt | Self-written monitors were unreliable. The `/loop` was replaced on 2026-09-21 by `glab:mr-watch`. Monitor stays out |
| 2026-07-02 | A human's thread may be resolved once it is truly addressed | Reversed the assistant's first rule "never resolve a human thread" |
| 2026-07-05 | Only the named MRs or the session's own MRs are in scope; never search for related MRs | Searching found unrelated MRs |
| 2026-07-06 | `babysit` runs at maximum autonomy and overrides cautious defaults during the loop | Mined runs showed agents stopping for permission |
| 2026-08-05 | The briefing holds only the final proposal, with no alternatives | Partly reversed on 2026-10-05: each owed decision shows its strongest rejected alternative |
| 2026-08-06 | The five personal commands become the `sdlc` plugin and name no CLI | The plugin has to work outside the maintainer's setup. The assistant argued to keep naming a tracker CLI and was overruled |
| 2026-08-06 | `ticket-new` status follows the work: in progress and assigned once work started, otherwise backlog | Replaces "always backlog" |
| 2026-08-07 | `glab-mr:babysit` moves to `sdlc:mr-babysit` with no deprecation stub, and `open-mr` becomes `mr-open` | Babysitting is a delivery stage. Exactly one babysit command exists. The `babysit:auto-reply` marker kept its name so old threads are not processed again |
| 2026-08-12 | `wrap-up` never looks a status up | The maintainer rejected a draft that checked merge and CI state: "what it doesn't know it shouldn't report" |
| 2026-08-14 | A sonnet subagent creates the ticket, and the orchestrator writes the body | Identifier lookups are mechanical. The body needs the session's context |
| 2026-08-14 | After the final validation, the plan continues into `mr-open`, then `mr-babysit` | The agent got stuck before opening the MR. The confirmation step was removed on 2026-08-24 |
| 2026-08-24 | One persistent implementation subagent, not one per step | A fresh subagent per step was "SUPER SLOW and PAINFUL", because each one explored the repository again |
| 2026-08-24 | Validators start cold, with only the plan | They must find flaws, not confirm the orchestrator's bias |
| 2026-08-24 | A 30-minute "continue the plan" cron | Agents announced work and then stopped |
| 2026-08-24 | Plan mode is entered only for the final writing | Plan mode blocked the explorations needed to settle the decisions |
| 2026-08-24 | Non-overlapping deep dives run in parallel; phases stay strictly in order | A wide map and a deep dive running at the same time is "nonsense". Independent dives only cost wall-clock time when serialized |
| 2026-08-25 | `mr-babysit` and `code-review:watch` mirror each other across the handshake | One side fixes, the other verifies. Watch resolves threads, and babysit replies |
| 2026-08-25 | Babysit resolves a watch thread only on the user's instruction | Resolving one is "a human decision, not action" |
| 2026-08-25 | After the handover, babysit waits for the ticket to come back | Before, a human restarted babysit after every rejection |
| 2026-08-25 | `glab` is a soft dependency only | Reversed the same day. Merging `glab-mr` into `glab` with `mr-status` made the skill, not the CLI, the dependency |
| 2026-08-25 | `glab:fix-all` dropped with no replacement | `mr-babysit` owns that loop |
| 2026-08-25 | The workflow states are resolved from loaded context first, and anything fetched from the API is offered for persistence | Avoids fetching the same facts again on every run. Moved to `teamwork:workflow-identify` on 2026-09-21 |
| 2026-09-02 | The `pre-plan` ticket subagent never opens the codebase; linked MRs give a diff stat only | The ticket subagent took "collect things" as an order to explore code |
| 2026-09-02 | `brief-next-steps` stays in sdlc, and `pre-plan` ends by running it | Moving it to `prose` was considered and rejected |
| 2026-09-03 | `ticket-attach-docs` is its own skill, run by `wrap-up` | Uploading early causes churn while the documents still change |
| 2026-09-05 | Every babysit comment is signed `<!-- sdlc:mr-babysit -->` | The marker also tells the run which threads it already handled |
| 2026-09-07 | Babysit split into an orchestrator skill and a worker skill. The worker triages and owns the ledger, and a fixer implements | Reversed on 2026-09-21: the worker skill is deleted, the orchestrator owns the ledger, and one actor does triage and implementation |
| 2026-09-07 | The worker sleeps between checks, sized to the pipeline (2–10 minutes) | Reversed on 2026-09-21: `glab:mr-watch` watches and nobody sleeps |
| 2026-09-07 | Babysit stops after 3 idle hours | Keeps a finished run from living forever |
| 2026-09-11 | The `mr-open` description fits one screen. The Why goes to the ticket, the reading guide and the release procedure to comments | Descriptions were "super fucking long" |
| 2026-09-11 | sdlc serves one task; multi-ticket planning is out of scope | A deliberate scope, stated in the README |
| 2026-09-11 | Commands became skills, with the same invocation and content | A marketplace-wide reorganization |
| 2026-09-11 | Skill names keep no plugin prefix | An unprefixed `/pre-plan` showed up once, but did not appear again |
| 2026-09-21 | `glab:mr-watch` watches, babysit decides, one actor acts. The worker skill and the sleeps are removed | A worker that ended its own turn to report made "an awkward interaction loop". One watcher serves babysit and watch alike |
| 2026-09-21 | A one-off sonnet subagent for batches that only post comments | Rejected the same day: "this split will only complicate it" |
| 2026-09-21 | The draft flag flips once. After that the ticket state alone shows whose turn it is | GitLab re-drafts on `fixup!` pushes, and the draft flag is not a universal handshake |
| 2026-09-21 | The `teamwork` plugin holds `workflow-identify` and `review-handshake` | Breaks the sdlc ↔ code-review dependency cycle |
| 2026-09-21 | No permission hook and no tool restriction on the watcher | Scope creep. `allowed-tools` frontmatter is enough |
| 2026-09-22 | Push guard, a re-raised dismissal becomes an ask, two more fix-evaluation questions, a stuck-pipeline event | Taken from another babysit implementation. Rejected: an `ask` on a file's fourth fix, and a force-with-lease escape hatch |
| 2026-10-01 | The `needs-human` state is entered only when every AI reviewer is satisfied with the current head. It replaces the fixed 2-minute quiet wait | The run handed over too early, or never noticed that everything it could do was done |
| 2026-10-01 | The turn ends with plain text in `needs-human`, not AskUserQuestion | A blocking question leaves the session stuck while the human is away, and the cache goes cold |
| 2026-10-01 | The watcher's poll interval must be 30–90 seconds; the waiting cadence moved from 300 to 90 seconds | Agents set intervals too high and changes were noticed late |
| 2026-10-01 | Pending drafts are ignored, and the run never writes draft comments | A reviewer and babysit can run under the same user. A draft on its own MR would make the author a reviewer |
| 2026-10-05 | Every open decision in `pre-plan` gets a recommended approach and the rejected alternatives, each with a reason. The briefing shows only the strongest alternative | The user wants to see why the recommendation wins without reading the argument again |

## How changes are checked

`make all` must pass: the repository checks in `scripts/check.sh` (manifests, marketplace and README consistency, frontmatter, references, this file's sections), `claude plugin validate --strict`, and the hook tests. sdlc has no hooks, so for this plugin the checks are structural. They do not test behavior.

sdlc has no eval suite. As of 2026-10-05 the private `claude-code-plugins-evals` repository covers only `prose`. A session that changes a skill says so in its summary instead of claiming the change was measured.

Until evals exist, behavior changes are checked as follows:

1. Mine real runs from `~/.claude/projects` for the skill's failures and for the user's corrections. Every major `mr-babysit` change started this way (2026-07-05, 2026-07-06, 2026-08-25, 2026-09-22).
2. Run the changed skill, or the scripts it depends on, against a real MR, read-only where possible. Keep every private identifier (hosts, projects, MR numbers, tickets) out of the repository. The pre-commit hook enforces this.
3. Re-read the touched skills for size and for consistency with `code-review:watch`, `teamwork` and `glab`.
4. Leave the change staged or in a worktree, so the maintainer can review it before anything is pushed.
